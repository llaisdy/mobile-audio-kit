from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.id3 import TPE1, TALB

class AudioFormatHandler:
    """Base handler with default implementations"""
    @staticmethod
    def get_encoding(audio):
        if hasattr(audio.info, 'codec'):
            return audio.info.codec
        elif hasattr(audio.info, 'codec_name'):
            return audio.info.codec_name
        else:
            return audio.info.__class__.__name__
    
    @staticmethod
    def get_artist(audio):
        return str(audio.get('artist', [''])[0]) if 'artist' in audio else None
    
    @staticmethod
    def set_artist(audio, value):
        audio['artist'] = [value]
    
    @staticmethod
    def get_album(audio):
        return str(audio.get('album', [''])[0]) if 'album' in audio else None
    
    @staticmethod
    def set_album(audio, value):
        audio['album'] = [value]
    
    @staticmethod
    def has_image(audio):
        return False
    
    @staticmethod
    def get_image_info(audio):
        return None

    @staticmethod
    def extract_image(audio):
        """
        Extract image data and mime type from audio file.
        
        Returns:
            tuple: (image_data, mime_type)
        
        Raises:
            ValueError: If no image is found
        """
        raise ValueError("No image found or unsupported format")
    
    @staticmethod
    def set_image(audio, image_data, mime_type="image/jpeg"):
        raise NotImplementedError("Setting images not implemented for this format")


class MP3Handler(AudioFormatHandler):
    @staticmethod
    def get_encoding(audio):
        return 'mp3'
    
    @staticmethod
    def get_artist(audio):
        return str(audio.get('TPE1', [''])[0]) if 'TPE1' in audio else None
    
    @staticmethod
    def set_artist(audio, value):
        audio['TPE1'] = TPE1(encoding=3, text=[value])
    
    @staticmethod
    def get_album(audio):
        return str(audio.get('TALB', [''])[0]) if 'TALB' in audio else None
    
    @staticmethod
    def set_album(audio, value):
        audio['TALB'] = TALB(encoding=3, text=[value])
    
    @staticmethod
    def has_image(audio):
        return any(k.startswith('APIC:') for k in audio.keys())
    
    @staticmethod
    def get_image_info(audio):
        apic_frames = [audio[k] for k in audio if k.startswith('APIC:')]
        if not apic_frames:
            return None
        
        apic = apic_frames[0]  # Get first image
        return {
            'format': apic.mime,
            'type': apic.type,  # 3 is cover front
            'desc': apic.desc,
            'size': len(apic.data)
        }

    @staticmethod
    def extract_image(audio):
        apic_frames = [audio[k] for k in audio if k.startswith('APIC:')]
        if not apic_frames:
            raise ValueError("No image found in MP3 file")
        
        apic = apic_frames[0]  # Get first image
        return apic.data, apic.mime
    
    @staticmethod
    def set_image(audio, image_data, mime_type="image/jpeg"):
        from mutagen.id3 import APIC
        audio['APIC'] = APIC(
            encoding=3,
            mime=mime_type,
            type=3,  # Cover (front)
            desc='Cover',
            data=image_data
        )


class MP4Handler(AudioFormatHandler):
    @staticmethod
    def get_artist(audio):
        return str(audio.get('\xa9ART', [''])[0]) if '\xa9ART' in audio else None
    
    @staticmethod
    def set_artist(audio, value):
        audio['\xa9ART'] = [value]
    
    @staticmethod
    def get_album(audio):
        return str(audio.get('\xa9alb', [''])[0]) if '\xa9alb' in audio else None
    
    @staticmethod
    def set_album(audio, value):
        audio['\xa9alb'] = [value]
    
    @staticmethod
    def has_image(audio):
        return 'covr' in audio
    
    @staticmethod
    def get_image_info(audio):
        if 'covr' not in audio:
            return None
        
        cover = audio['covr'][0]
        format_type = 'jpeg' if cover.imageformat == cover.FORMAT_JPEG else 'png'
        return {
            'format': f'image/{format_type}',
            'size': len(cover)
        }

    @staticmethod
    def extract_image(audio):
        if 'covr' not in audio:
            raise ValueError("No image found in M4A file")
        
        cover = audio['covr'][0]
        format_type = 'image/jpeg' if cover.imageformat == cover.FORMAT_JPEG else 'image/png'
        return bytes(cover), format_type
    
    @staticmethod
    def set_image(audio, image_data, mime_type="image/jpeg"):
        from mutagen.mp4 import MP4Cover
        format_type = MP4Cover.FORMAT_JPEG if mime_type == "image/jpeg" else MP4Cover.FORMAT_PNG
        audio['covr'] = [MP4Cover(image_data, format_type)]


class FLACHandler(AudioFormatHandler):
    @staticmethod
    def get_encoding(audio):
        return 'flac'  # Explicitly return 'flac' instead of the class name
    
    @staticmethod
    def get_artist(audio):
        return str(audio.get('artist', [''])[0]) if 'artist' in audio else None
    
    @staticmethod
    def get_album(audio):
        return str(audio.get('album', [''])[0]) if 'album' in audio else None
    
    @staticmethod
    def has_image(audio):
        return bool(audio.pictures)
    
    @staticmethod
    def get_image_info(audio):
        if not audio.pictures:
            return None
        
        pic = audio.pictures[0]  # Get first image
        return {
            'format': pic.mime,
            'type': pic.type,
            'desc': pic.desc,
            'size': len(pic.data)
        }

    @staticmethod
    def extract_image(audio):
        if not audio.pictures:
            raise ValueError("No image found in FLAC file")
        
        pic = audio.pictures[0]  # Get first image
        return pic.data, pic.mime
    
    @staticmethod
    def set_image(audio, image_data, mime_type="image/jpeg"):
        from mutagen.flac import Picture
        pic = Picture()
        pic.data = image_data
        pic.type = 3  # Cover (front)
        pic.mime = mime_type
        audio.add_picture(pic)
