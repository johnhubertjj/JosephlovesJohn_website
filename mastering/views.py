from django.shortcuts import render


def home(request):
    return render(
        request,
        "mastering/home.html",
        {"entered_from_home": request.GET.get("from_home") == "1"},
    )


def subfolder(request, subfolder):
    return render(
        request,
        "mastering/subfolder.html",
        {"subfolder": subfolder},
    )
