# forms.py
from django import forms

class VideoForm(forms.Form):
    link = forms.URLField(label='YouTube Video Link')
