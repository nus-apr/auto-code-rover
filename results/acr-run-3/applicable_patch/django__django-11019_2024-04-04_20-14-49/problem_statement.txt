Merging 3 or more media objects can throw unnecessary MediaOrderConflictWarnings
Description
	
Consider the following form definition, where text-editor-extras.js depends on text-editor.js but all other JS files are independent:
from django import forms
class ColorPicker(forms.Widget):
	class Media:
		js = ['color-picker.js']
class SimpleTextWidget(forms.Widget):
	class Media:
		js = ['text-editor.js']
class FancyTextWidget(forms.Widget):
	class Media:
		js = ['text-editor.js', 'text-editor-extras.js', 'color-picker.js']
class MyForm(forms.Form):
	background_color = forms.CharField(widget=ColorPicker())
	intro = forms.CharField(widget=SimpleTextWidget())
	body = forms.CharField(widget=FancyTextWidget())
Django should be able to resolve the JS files for the final form into the order text-editor.js, text-editor-extras.js, color-picker.js. However, accessing MyForm().media results in:
/projects/django/django/forms/widgets.py:145: MediaOrderConflictWarning: Detected duplicate Media files in an opposite order:
text-editor-extras.js
text-editor.js
 MediaOrderConflictWarning,
Media(css={}, js=['text-editor-extras.js', 'color-picker.js', 'text-editor.js'])
The MediaOrderConflictWarning is a result of the order that the additions happen in: ColorPicker().media + SimpleTextWidget().media produces Media(css={}, js=['color-picker.js', 'text-editor.js']), which (wrongly) imposes the constraint that color-picker.js must appear before text-editor.js.
The final result is particularly unintuitive here, as it's worse than the "naïve" result produced by Django 1.11 before order-checking was added (color-picker.js, text-editor.js, text-editor-extras.js), and the pair of files reported in the warning message seems wrong too (aren't color-picker.js and text-editor.js the wrong-ordered ones?)
