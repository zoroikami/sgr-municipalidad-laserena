"""Filesystem media cannot produce public URLs; only the authorized photo view serves it."""
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivatePhotoStorage(FileSystemStorage):
    def url(self, name):
        raise ValueError('Las fotos se consultan mediante la vista autenticada.')


private_photo_storage = PrivatePhotoStorage()
