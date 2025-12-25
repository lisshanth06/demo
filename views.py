from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import Project, Source

from openai import OpenAI
import tempfile
import os

from ai_engine.embeddings import embed_text, chunk_text
from ai_engine.vector_store import upsert_text_chunks, ensure_collection
from ai_engine.rag import answer_question

# -----------------------------------
# OpenAI client (uses env key)
# -----------------------------------
client = OpenAI()

# -----------------------------------
# HTMX Helper Function
# -----------------------------------
def is_htmx(request):
    """Check if request is from HTMX"""
    return request.headers.get('HX-Request') == 'true'

# -----------------------------------
# PROJECT LIST
# -----------------------------------
def project_list(request):
    projects = Project.objects.all()
    template = "writer/project_list.html"
    return render(request, template, {"projects": projects})

# -----------------------------------
# CREATE PROJECT
# -----------------------------------
def create_project(request):
    if request.method == "POST":
        name = request.POST.get("name")
        if name:
            Project.objects.create(name=name)
            # Return project list for HTMX
            if is_htmx(request):
                return project_list(request)
            return redirect("/")
    return render(request, "writer/create_project.html")

# -----------------------------------
# PROJECT DETAIL
# -----------------------------------
def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    sources = project.source_set.all()

    answer = None

    if request.method == "POST" and "question" in request.POST:
        question = request.POST["question"]
        source_ids = [str(s.id) for s in sources]
        answer = answer_question(question, source_ids)
        
        # Return only answer section for HTMX
        if is_htmx(request):
            return render(request, "writer/answer_section.html", {
                "answer": answer
            })

    return render(request, "writer/project_detail.html", {
        "project": project,
        "sources": sources,
        "answer": answer,
    })

# -----------------------------------
# ADD TEXT SOURCE
# -----------------------------------
def add_text_source(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if request.method == "POST":
        title = request.POST.get("title")
        text = request.POST.get("text")

        if title and text:
            source = Source.objects.create(
                project=project,
                title=title,
                text=text,
                source_type="text",
            )
            
            # Add to vector DB
            ensure_collection()
            chunks = chunk_text(text)
            vectors = [embed_text(c) for c in chunks]
            upsert_text_chunks(str(source.id), chunks, vectors)

        # Return project detail for HTMX
        if is_htmx(request):
            return project_detail(request, project.id)
        return redirect(f"/project/{project.id}/")

    return render(
        request,
        "writer/add_source.html",
        {
            "project": project,
            "type": "text",
        },
    )

# -----------------------------------
# WEB SEARCH SOURCE
# -----------------------------------
def web_search_source(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if request.method == "POST":
        query = request.POST.get("query")

        if query:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Explain the following topic clearly in 5–6 short factual lines:\n\n"
                            f"{query}"
                        ),
                    }
                ],
            )

            summary = response.choices[0].message.content.strip()

            source = Source.objects.create(
                project=project,
                title=f"Web search: {query}",
                text=summary,
                source_type="web",
            )
            
            # Add to vector DB
            ensure_collection()
            chunks = chunk_text(summary)
            vectors = [embed_text(c) for c in chunks]
            upsert_text_chunks(str(source.id), chunks, vectors)

        # Return project detail for HTMX
        if is_htmx(request):
            return project_detail(request, project.id)
        return redirect(f"/project/{project.id}/")

    return redirect(f"/project/{project.id}/")

# -----------------------------------
# ADD AUDIO SOURCE
# -----------------------------------
def add_audio_source(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if request.method == "POST":
        title = request.POST.get("title")
        audio_file = request.FILES.get("file")

        if not audio_file:
            if is_htmx(request):
                return project_detail(request, project.id)
            return redirect(f"/project/{project.id}/")

        # Save DB row first
        source = Source.objects.create(
            project=project,
            title=title or audio_file.name,
            source_type="audio",
            text=""
        )

        # Save temp file
        suffix = os.path.splitext(audio_file.name)[1]

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            for chunk in audio_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        # Transcribe
        with open(tmp_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                file=f,
                model="gpt-4o-transcribe"
            )

        text = transcript.text
        source.text = text
        source.save()

        # Add to vector DB
        ensure_collection()
        chunks = chunk_text(text)
        vectors = [embed_text(c) for c in chunks]
        upsert_text_chunks(str(source.id), chunks, vectors)

        os.remove(tmp_path)

        # Return project detail for HTMX
        if is_htmx(request):
            return project_detail(request, project.id)
        return redirect(f"/project/{project.id}/")

    return render(request, "writer/add_source.html", {
        "project": project,
        "type": "audio"
    })

# -----------------------------------
# EDIT PROJECT
# -----------------------------------
def edit_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if request.method == "POST":
        name = request.POST.get("name")
        if name:
            project.name = name
            project.save()
        
        # Return project detail for HTMX
        if is_htmx(request):
            return project_detail(request, project.id)
        return redirect(f"/project/{project.id}/")

    return render(
        request,
        "writer/edit_project.html",
        {"project": project},
    )

# -----------------------------------
# DELETE PROJECT
# -----------------------------------
def delete_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    project.delete()
    
    # Return project list for HTMX
    if is_htmx(request):
        return project_list(request)
    return redirect("/")

# -----------------------------------
# EDIT SOURCE
# -----------------------------------
def edit_source(request, source_id):
    source = get_object_or_404(Source, id=source_id)

    if request.method == "POST":
        title = request.POST.get("title")
        text = request.POST.get("text")

        if title:
            source.title = title
        if text:
            source.text = text

        source.save()
        
        # Update vector DB
        ensure_collection()
        chunks = chunk_text(source.text)
        vectors = [embed_text(c) for c in chunks]
        upsert_text_chunks(str(source.id), chunks, vectors)
        
        # Return project detail for HTMX
        if is_htmx(request):
            return project_detail(request, source.project.id)
        return redirect(f"/project/{source.project.id}/")

    return render(
        request,
        "writer/edit_source.html",
        {"source": source},
    )

# -----------------------------------
# DELETE SOURCE
# -----------------------------------
def delete_source(request, source_id):
    source = get_object_or_404(Source, id=source_id)
    project_id = source.project.id
    source.delete()
    
    # Return project detail for HTMX
    if is_htmx(request):
        return project_detail(request, project_id)
    return redirect(f"/project/{project_id}/")  