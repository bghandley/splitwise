import spacy
import nltk
from collections import Counter, defaultdict
from textblob import TextBlob
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime
from flask import current_app
import json
import os

class TranscriptAnalyzer:
    def __init__(self, app=None):
        self.app = app
        self.nlp = None
        self.stopwords = set()
        
        if app:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        # Load NLP models and resources
        self.nlp = spacy.load("en_core_web_sm")
        nltk.download('punkt')
        nltk.download('stopwords')
        nltk.download('maxent_ne_chunker')
        nltk.download('words')
        self.stopwords = set(nltk.corpus.stopwords.words('english'))

    def analyze_transcript(self, transcript):
        """Perform comprehensive analysis of transcript"""
        # Combine all segments into full text
        full_text = " ".join(segment["text"] for segment in transcript["segments"])
        doc = self.nlp(full_text)
        
        # Basic statistics
        word_count = len(full_text.split())
        sentence_count = len(list(doc.sents))
        
        analysis = {
            "basic_stats": self._get_basic_stats(transcript),
            "speaker_analysis": self._analyze_speakers(transcript),
            "content_analysis": self._analyze_content(doc),
            "sentiment_analysis": self._analyze_sentiment(transcript),
            "topic_analysis": self._extract_topics(doc),
            "key_phrases": self._extract_key_phrases(doc),
            "word_cloud": self._generate_word_cloud(full_text),
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return analysis

    def _get_basic_stats(self, transcript):
        """Get basic transcript statistics"""
        segments = transcript["segments"]
        total_duration = transcript["duration"]
        
        # Calculate words per minute
        total_words = sum(len(segment["text"].split()) for segment in segments)
        words_per_minute = (total_words / total_duration) * 60 if total_duration > 0 else 0
        
        return {
            "duration": total_duration,
            "total_segments": len(segments),
            "total_words": total_words,
            "words_per_minute": round(words_per_minute, 2),
            "total_speakers": len(transcript.get("speakers", [])),
            "average_segment_length": round(total_duration / len(segments), 2)
        }

    def _analyze_speakers(self, transcript):
        """Analyze speaker participation and patterns"""
        speakers = defaultdict(lambda: {
            "segments": 0,
            "words": 0,
            "total_duration": 0,
            "average_segment_duration": 0,
            "interruptions": 0,
            "questions_asked": 0
        })
        
        prev_speaker = None
        
        for segment in transcript["segments"]:
            speaker = segment.get("speaker", "Unknown Speaker")
            duration = segment["end"] - segment["start"]
            text = segment["text"]
            
            # Update speaker stats
            speakers[speaker]["segments"] += 1
            speakers[speaker]["words"] += len(text.split())
            speakers[speaker]["total_duration"] += duration
            
            # Check for interruptions
            if prev_speaker and prev_speaker != speaker:
                speakers[speaker]["interruptions"] += 1
            
            # Count questions
            if "?" in text:
                speakers[speaker]["questions_asked"] += 1
            
            prev_speaker = speaker
        
        # Calculate averages
        for speaker_stats in speakers.values():
            speaker_stats["average_segment_duration"] = round(
                speaker_stats["total_duration"] / speaker_stats["segments"], 2
            )
        
        return dict(speakers)

    def _analyze_content(self, doc):
        """Analyze content patterns and structure"""
        # Extract named entities
        entities = defaultdict(list)
        for ent in doc.ents:
            entities[ent.label_].append(ent.text)
        
        # Get most common words (excluding stopwords)
        words = [token.text.lower() for token in doc 
                if not token.is_stop and not token.is_punct and token.text.strip()]
        word_freq = Counter(words).most_common(20)
        
        return {
            "named_entities": {k: list(set(v)) for k, v in entities.items()},
            "top_words": dict(word_freq),
            "vocabulary_richness": len(set(words)) / len(words) if words else 0
        }

    def _analyze_sentiment(self, transcript):
        """Analyze sentiment throughout the transcript"""
        overall_sentiment = TextBlob(" ".join(s["text"] for s in transcript["segments"]))
        
        # Track sentiment over time
        sentiment_timeline = []
        window_size = max(1, len(transcript["segments"]) // 10)  # 10 points
        
        for i in range(0, len(transcript["segments"]), window_size):
            window_text = " ".join(s["text"] for s in 
                                 transcript["segments"][i:i + window_size])
            sentiment = TextBlob(window_text)
            
            sentiment_timeline.append({
                "timestamp": transcript["segments"][i]["start"],
                "polarity": sentiment.sentiment.polarity,
                "subjectivity": sentiment.sentiment.subjectivity
            })
        
        return {
            "overall": {
                "polarity": overall_sentiment.sentiment.polarity,
                "subjectivity": overall_sentiment.sentiment.subjectivity
            },
            "timeline": sentiment_timeline
        }

    def _extract_topics(self, doc):
        """Extract main topics and subtopics"""
        # Use noun chunks as potential topics
        noun_chunks = list(doc.noun_chunks)
        
        # Group by root dependencies
        topics = defaultdict(list)
        for chunk in noun_chunks:
            root = chunk.root.head.text
            if not chunk.root.is_stop:
                topics[root].append(chunk.text)
        
        # Sort by frequency and relevance
        return {
            topic: subtopics 
            for topic, subtopics in topics.items()
            if len(subtopics) > 1  # Filter out single-occurrence topics
        }

    def _extract_key_phrases(self, doc):
        """Extract key phrases and expressions"""
        key_phrases = []
        
        for sent in doc.sents:
            # Look for subject-verb-object patterns
            for token in sent:
                if token.dep_ == "nsubj" and token.head.pos_ == "VERB":
                    # Get the full phrase
                    phrase = self._get_phrase_span(token)
                    if phrase:
                        key_phrases.append({
                            "text": phrase.text,
                            "type": "subject-verb",
                            "root_verb": token.head.text
                        })
        
        return key_phrases[:10]  # Return top 10 key phrases

    def _get_phrase_span(self, token):
        """Get the full span of a phrase starting from a token"""
        lefts = list(token.lefts)
        rights = list(token.rights)
        if not lefts and not rights:
            return None
        
        start = min([t.i for t in lefts] + [token.i])
        end = max([t.i for t in rights] + [token.i])
        return token.doc[start:end + 1]

    def _generate_word_cloud(self, text):
        """Generate word cloud image from text"""
        try:
            wordcloud = WordCloud(
                width=800,
                height=400,
                background_color='white',
                stopwords=self.stopwords
            ).generate(text)
            
            # Convert to base64 image
            img_buffer = io.BytesIO()
            wordcloud.to_image().save(img_buffer, format='PNG')
            img_str = base64.b64encode(img_buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
        except Exception as e:
            current_app.logger.error(f"Word cloud generation failed: {str(e)}")
            return None

    def save_analysis(self, analysis, output_path):
        """Save analysis results to file"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to save analysis: {str(e)}")
            return False

    def get_analysis_path(self, episode_id):
        """Get analysis file path for episode"""
        return os.path.join(
            current_app.config['ANALYSIS_DIR'],
            f'episode_{episode_id}',
            'analysis.json'
        )

    def ensure_analysis(self, episode):
        """Ensure analysis exists for episode, generate if needed"""
        analysis_path = self.get_analysis_path(episode.id)
        
        if os.path.exists(analysis_path):
            with open(analysis_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        from .transcript_generator import TranscriptGenerator
        transcript_gen = TranscriptGenerator(self.app)
        transcript = transcript_gen.ensure_transcript(episode)
        
        if transcript:
            analysis = self.analyze_transcript(transcript)
            self.save_analysis(analysis, analysis_path)
            return analysis
        
        return None

# Example usage:
"""
from flask import Flask, jsonify
app = Flask(__name__)

# Initialize analyzer
analyzer = TranscriptAnalyzer(app)

@app.route('/api/episodes/<int:episode_id>/analysis', methods=['GET'])
def get_episode_analysis(episode_id):
    episode = Episode.query.get_or_404(episode_id)
    analysis = analyzer.ensure_analysis(episode)
    
    if analysis:
        return jsonify(analysis)
    
    return jsonify({'error': 'Analysis not found'}), 404
"""
