import re

from django import forms

from .consulta import CODE_ALPHABET, normalise_code


class PublicConsultationForm(forms.Form):
    folio = forms.CharField(label='Folio de la atención', max_length=35,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off', 'autocapitalize': 'characters', 'spellcheck': 'false'}),
        help_text='Lo encontrarás en el correo que recibiste de la municipalidad.')
    codigo = forms.CharField(label='Código privado', max_length=64,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'one-time-code', 'autocapitalize': 'characters', 'spellcheck': 'false'}),
        help_text='Copia el código del correo. Puedes pegarlo con o sin guiones.')

    def clean_folio(self):
        folio = self.cleaned_data['folio'].strip().upper()
        if not re.fullmatch(r'ATN-[0-9]{4}-[0-9]{4,}', folio):
            raise forms.ValidationError('Ingresa el folio completo que aparece en tu correo.')
        return folio

    def clean_codigo(self):
        code = normalise_code(self.cleaned_data['codigo'])
        if len(code) != 20 or any(character not in CODE_ALPHABET for character in code):
            raise forms.ValidationError('Ingresa el código privado completo que aparece en tu correo.')
        return code
