from feedgen.feed import FeedGenerator
from datetime import datetime
from flask import url_for
from mutagen.mp3 import MP3
import os

class PodcastFeed:
    def __init__(self, app):
        self.app = app
        self.base_url = app.config['BASE_URL']
        self.podcast_title = "Spirit of the Deal"
        self.podcast_description = "Weekly conversations about spiritual business practices and conscious entrepreneurship"
        self.podcast_author = "Spirit of the Deal"
        self.podcast_email = "podcast@spiritofthedeal.com"
        self.podcast_image = f"{self.base_url}/static/images/podcast-cover.jpg"
        self.podcast_category = "Business"
        self.podcast_subcategory = "Entrepreneurship"
        self.explicit = "no"

    def generate_feed(self, episodes):
        """Generate RSS feed for podcast episodes"""
        fg = FeedGenerator()
        fg.load_extension('podcast')

        # Set feed metadata
        fg.title(self.podcast_title)
        fg.description(self.podcast_description)
        fg.author({'name': self.podcast_author, 'email': self.podcast_email})
        fg.link(href=self.base_url, rel='alternate')
        fg.logo(self.podcast_image)
        fg.subtitle(self.podcast_description)
        fg.language('en')
        
        # iTunes specific tags
        fg.podcast.itunes_category(self.podcast_category, self.podcast_subcategory)
        fg.podcast.itunes_explicit(self.explicit)
        fg.podcast.itunes_author(self.podcast_author)
        fg.podcast.itunes_owner(name=self.podcast_author, email=self.podcast_email)
        fg.podcast.itunes_image(self.podcast_image)

        # Add episodes
        for episode in episodes:
            fe = fg.add_entry()
            fe.id(episode.guid)
            fe.title(episode.title)
            fe.description(episode.description)
            
            # Episode audio file
            audio_url = f"{self.base_url}/media/podcast/{episode.audio_file}"
            fe.enclosure(audio_url, str(episode.file_size), 'audio/mpeg')
            
            # Episode metadata
            fe.published(episode.published_at)
            fe.link(href=f"{self.base_url}/podcast/{episode.slug}")
            
            # iTunes specific episode tags
            fe.podcast.itunes_duration(self._get_audio_duration(episode.audio_file))
            fe.podcast.itunes_season(episode.season)
            fe.podcast.itunes_episode(episode.episode_number)
            fe.podcast.itunes_episodeType('full')
            if episode.image:
                fe.podcast.itunes_image(f"{self.base_url}/media/podcast/{episode.image}")

        return fg.rss_str(pretty=True)

    def _get_audio_duration(self, audio_file):
        """Get duration of audio file in HH:MM:SS format"""
        try:
            file_path = os.path.join(self.app.root_path, 'media', 'podcast', audio_file)
            audio = MP3(file_path)
            duration = int(audio.info.length)
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            seconds = duration % 60
            
            if hours > 0:
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes:02d}:{seconds:02d}"
        except Exception as e:
            print(f"Error getting audio duration: {e}")
            return "00:00"

    def generate_episode_guid(self, episode):
        """Generate a unique GUID for an episode"""
        return f"{self.base_url}/podcast/{episode.slug}"

    def validate_audio_file(self, file_path):
        """Validate audio file format and metadata"""
        try:
            audio = MP3(file_path)
            return {
                'valid': True,
                'duration': int(audio.info.length),
                'bitrate': audio.info.bitrate,
                'sample_rate': audio.info.sample_rate,
                'channels': audio.info.channels
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }

    def optimize_audio(self, input_path, output_path, target_bitrate='192k'):
        """Optimize audio file for podcast distribution"""
        try:
            from pydub import AudioSegment
            
            # Load audio file
            audio = AudioSegment.from_mp3(input_path)
            
            # Convert to mono if needed
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Export with optimal settings
            audio.export(
                output_path,
                format='mp3',
                bitrate=target_bitrate,
                parameters=["-q:a", "0"]  # Use highest quality VBR encoding
            )
            
            return True
        except Exception as e:
            print(f"Error optimizing audio: {e}")
            return False

# Example usage:
"""
# Initialize feed generator
feed_generator = PodcastFeed(app)

# Generate feed
episodes = Episode.query.filter_by(status='published').order_by(Episode.published_at.desc()).all()
feed_xml = feed_generator.generate_feed(episodes)

# Save feed
with open('podcast.xml', 'wb') as f:
    f.write(feed_xml)

# Optimize new episode audio
feed_generator.optimize_audio(
    'raw_episode.mp3',
    'optimized_episode.mp3'
)
"""
