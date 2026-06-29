"""Forms for the mastering services site."""

from django import forms


class MasteringIntakeForm(forms.Form):
    """Capture detailed project information for a mastering job."""

    submitter_role = forms.ChoiceField(
        label="Are you an artist or engineer?",
        choices=[
            ("artist", "I am the artist"),
            ("engineer", "I am the mix engineer"),
        ],
        widget=forms.RadioSelect,
    )
    contact_email = forms.EmailField(
        label="Contact email",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "inputmode": "email"}),
    )
    engineer_name = forms.CharField(
        label="Engineer name",
        max_length=160,
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "name"}),
    )
    client_contact_email = forms.EmailField(
        label="Artist / client email",
        required=False,
        widget=forms.EmailInput(attrs={"autocomplete": "email", "inputmode": "email"}),
        help_text="Optional, only if the artist should be copied into project discussion.",
    )
    artist_name = forms.CharField(
        label="Artist name",
        max_length=160,
        widget=forms.TextInput(attrs={"autocomplete": "organization"}),
    )
    track_title = forms.CharField(label="Track title", max_length=180)
    album_or_ep = forms.CharField(label="Album / EP", max_length=180, required=False)
    isrc_code = forms.CharField(label="ISRC code", max_length=40, required=False)
    mix_file_details = forms.CharField(
        label="Mix file details",
        required=False,
        max_length=1200,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Include anything useful about the file, folder, or export.",
    )
    mix_file_link = forms.URLField(
        label="Mix file link",
        required=False,
        help_text=(
            "Upload the final WAV or AIFF to Google Drive, Dropbox, WeTransfer, or similar, "
            "then paste the share link here."
        ),
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "inputmode": "url",
                "placeholder": "https://...",
            }
        ),
    )
    sample_rate = forms.CharField(
        label="What is the sample rate?",
        required=False,
        max_length=80,
        help_text="For example: 44.1kHz or 48kHz.",
    )
    bit_depth = forms.CharField(
        label="What is the bit depth?",
        required=False,
        max_length=80,
        help_text="For example: 24-bit or 32-bit float.",
    )
    peak_loudness_level = forms.CharField(
        label="What is the peak loudness level?",
        required=False,
        max_length=120,
        help_text="If known.",
    )
    master_bus_processing = forms.CharField(
        label="Is there any processing on the master bus?",
        required=False,
        max_length=1200,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Compression, saturation, EQ, etc. This is just for the audio output to WAV or AIFF.",
    )
    limiting_clipping = forms.CharField(
        label="Is there any limiting, clipping, or loudness maximisation?",
        required=False,
        max_length=1200,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Mention any limiters, clipping, or loudness processing already on the mix.",
    )
    desired_feel = forms.CharField(
        label="What do you want the master to feel like?",
        required=False,
        max_length=1600,
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    mix_concerns = forms.CharField(
        label="Do you have any specific concerns with the mix?",
        required=False,
        max_length=1600,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Low end, vocals, brightness, or anything else you want checked.",
    )
    reference_tracks = forms.URLField(
        label="Reference track link",
        required=False,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "inputmode": "url",
                "placeholder": "https://...",
            }
        ),
        help_text="Paste a Spotify, YouTube, Drive, Dropbox, or similar reference link.",
    )
    reference_track_notes = forms.CharField(
        label="What do you like about the reference track?",
        required=False,
        max_length=1600,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Tone, loudness, width, balance, punchiness, clarity, low end, highs, etc.",
    )
    release_formats = forms.MultipleChoiceField(
        label="Intended release format(s)",
        required=False,
        choices=[
            ("Streaming", "Streaming"),
            ("CD", "CD"),
            ("Vinyl", "Vinyl"),
            ("Social/video", "Social/video"),
            ("Other", "Other"),
        ],
        widget=forms.CheckboxSelectMultiple,
    )
    deliverables = forms.MultipleChoiceField(
        label="Deliverables",
        required=False,
        choices=[
            ("WAV", "WAV"),
            ("AIFF", "AIFF"),
            ("MP3 reference", "MP3 reference"),
            ("Instrumental", "Instrumental"),
            ("Clean/radio edit", "Clean/radio edit"),
            ("Other", "Other"),
        ],
        widget=forms.CheckboxSelectMultiple,
    )
    upload_confirmation = forms.URLField(
        label="Artist track upload",
        required=False,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "inputmode": "url",
                "placeholder": "https://...",
            }
        ),
        help_text="Paste the Google Drive, Dropbox, WeTransfer, or similar link for the artist track upload.",
    )
    artist_loudness_processing = forms.CharField(
        label="Loudness and Processing (if known)",
        required=False,
        max_length=1200,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Tell me anything you know about loudness, clipping, limiting, or processing already on the file.",
    )
    genre_vibe = forms.CharField(
        label="What is the Genre/vibe you are looking for?",
        required=False,
        max_length=1200,
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    artist_final_feel = forms.CharField(
        label="How should the final master feel?",
        required=False,
        max_length=1600,
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    artist_reference_tracks = forms.URLField(
        label="Reference track link",
        required=False,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "inputmode": "url",
                "placeholder": "https://...",
            }
        ),
        help_text="Paste a Spotify, YouTube, Drive, Dropbox, or similar reference link.",
    )
    artist_reference_notes = forms.CharField(
        label="What did you like about the reference track?",
        required=False,
        max_length=1600,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Loudness, tone, clarity, bass, highs, lows, width, or anything else.",
    )
    artist_release_formats = forms.MultipleChoiceField(
        label="Release format - Where will this be released?",
        required=False,
        choices=[
            ("Streaming", "Streaming"),
            ("Bandcamp", "Bandcamp"),
            ("CD", "CD"),
            ("Vinyl", "Vinyl"),
            ("Social/video", "Social/video"),
            ("Other", "Other"),
        ],
        widget=forms.CheckboxSelectMultiple,
    )
    artist_extra_notes = forms.CharField(
        label="Anything else you are unsure about or would like to add?",
        required=False,
        max_length=2400,
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    deadline = forms.DateField(
        label="Desired delivery date",
        required=False,
        input_formats=["%Y-%m-%d", "%d/%m/%Y", "%d %m %Y"],
        widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={
                "autocomplete": "off",
                "type": "date",
            }
        ),
    )
    hard_deadline = forms.ChoiceField(
        label="Is this a hard deadline?",
        required=False,
        choices=[
            ("", "No preference"),
            ("Yes", "Yes"),
            ("No", "No"),
        ],
    )
    multiple_tracks_notes = forms.CharField(
        label="Multiple track notes",
        required=False,
        max_length=1800,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="If there are multiple tracks, note whether they should all feel the same or differ by track.",
    )
    extra_notes = forms.CharField(
        label="Extra notes",
        required=False,
        max_length=2400,
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "tabindex": "-1",
                "aria-hidden": "true",
            }
        ),
    )

    def clean(self):
        """Validate the branch-specific required fields."""
        cleaned = super().clean() or {}
        role = cleaned.get("submitter_role")
        if role == "artist" and not cleaned.get("artist_name"):
            self.add_error("artist_name", "Please enter your artist name.")
        if role == "artist" and not cleaned.get("artist_final_feel"):
            self.add_error("artist_final_feel", "Please describe how the final master should feel.")
        if role == "artist" and not cleaned.get("upload_confirmation"):
            self.add_error("upload_confirmation", "Please provide an artist track upload link.")
        if role == "engineer" and not cleaned.get("engineer_name"):
            self.add_error("engineer_name", "Please enter the engineer name.")
        if role == "engineer" and not cleaned.get("mix_file_link"):
            self.add_error("mix_file_link", "Please provide a mix file link.")
        if role == "engineer" and not cleaned.get("sample_rate"):
            self.add_error("sample_rate", "Please enter the sample rate.")
        if role == "engineer" and not cleaned.get("bit_depth"):
            self.add_error("bit_depth", "Please enter the bit depth.")
        if role == "engineer" and not cleaned.get("desired_feel"):
            self.add_error("desired_feel", "Please describe what the master should feel like.")
        return cleaned
