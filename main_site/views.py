from django.shortcuts import render


def main(request):
    return render(request, "main_site/site.html", {"active_section": ""})


def intro(request):
    return render(request, "main_site/site.html", {"active_section": "intro"})


def music(request):
    return render(request, "main_site/site.html", {"active_section": "music"})


def art(request):
    return render(request, "main_site/site.html", {"active_section": "art"})


def contact(request):
    return render(request, "main_site/site.html", {"active_section": "contact"})
