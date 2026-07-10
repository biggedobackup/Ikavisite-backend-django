import logging
from io import BytesIO

from django.db import models
from PIL import Image

logger = logging.getLogger(__name__)


class CompressedImageField(models.ImageField):
    def __init__(self, *args, quality=70, max_size=(1920, 1920), **kwargs):
        self.quality = quality
        self.max_size = max_size
        super().__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        f = getattr(model_instance, self.attname)
        if f and not f._committed:
            try:
                if not hasattr(f, 'file') or not f.file:
                    return super().pre_save(model_instance, add)
                f.file.seek(0)
                img = Image.open(f.file)
                img = img.convert('RGB') if img.mode in ('RGBA', 'P') else img
                img.thumbnail(self.max_size, Image.LANCZOS)

                ext = f.name.lower().rsplit('.', 1)[-1] if '.' in f.name else 'jpg'
                fmt = 'JPEG' if ext in ('jpg', 'jpeg') else 'PNG'
                out = BytesIO()
                img.save(out, format=fmt, quality=self.quality, optimize=True)
                out.seek(0)

                f.file = out
                f.name = f.name.rsplit('.', 1)[0] + ('.jpg' if fmt == 'JPEG' else '.png')
            except Exception as exc:
                logger.warning(
                    'CompressedImageField.pre_save skip (%s): %s',
                    getattr(f, 'name', '?'), exc
                )
        return super().pre_save(model_instance, add)
