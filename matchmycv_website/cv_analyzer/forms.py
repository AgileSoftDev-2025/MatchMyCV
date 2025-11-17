from django import forms

class CVUploadForm(forms.Form):
    cv_file = forms.FileField()
    location = forms.CharField(max_length=50)

    def clean_cv_file(self):
        cv_file = self.cleaned_data.get('cv_file')
        if cv_file:
            if cv_file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File size exceeds 10 MB limit')
            if not cv_file.name.endswith('.pdf'):
                raise forms.ValidationError('Please upload a PDF file')
        return cv_file