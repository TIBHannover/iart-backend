# Generated by Django 3.1.7 on 2021-05-21 07:37

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('frontend', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='collection',
            name='height',
        ),
        migrations.RemoveField(
            model_name='collection',
            name='width',
        ),
        migrations.RemoveField(
            model_name='image',
            name='height',
        ),
        migrations.RemoveField(
            model_name='image',
            name='visible',
        ),
        migrations.RemoveField(
            model_name='image',
            name='width',
        ),
        migrations.AddField(
            model_name='collection',
            name='name',
            field=models.CharField(default='', max_length=256),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='collection',
            name='progress',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='collection',
            name='status',
            field=models.CharField(choices=[('U', 'Upload'), ('R', 'Ready')], default='U', max_length=2),
        ),
        migrations.AddField(
            model_name='collection',
            name='user',
            field=models.ForeignKey(default=0, on_delete=django.db.models.deletion.CASCADE, to='auth.user'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='collection',
            name='visible',
            field=models.CharField(choices=[('V', 'Visible'), ('A', 'Authenticated'), ('U', 'User')], default='U', max_length=2),
        ),
    ]