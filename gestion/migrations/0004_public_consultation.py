from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('gestion', '0003_restore_section_codes')]
    operations = [
        migrations.AddField(model_name='atencion', name='solicitante_email',
            field=models.EmailField(blank=True, default='', max_length=254, verbose_name='Correo del solicitante')),
        migrations.AddField(model_name='atencion', name='consulta_codigo_hash',
            field=models.CharField(blank=True, default='', editable=False, max_length=64)),
        migrations.AddField(model_name='atencion', name='consulta_enviado_at',
            field=models.DateTimeField(blank=True, editable=False, null=True)),
    ]
