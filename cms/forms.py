from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectField, FileField, SelectMultipleField, FloatField, DateTimeField
from wtforms.validators import DataRequired, Length, Email, Optional
from flask_wtf.file import FileAllowed

class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Content', validators=[DataRequired()])
    excerpt = TextAreaField('Excerpt', validators=[Optional(), Length(max=500)])
    featured_image = FileField('Featured Image', validators=[
        Optional(),
        FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')
    ])
    category = SelectField('Category', coerce=int)
    tags = SelectMultipleField('Tags', coerce=int)
    meta_description = TextAreaField('Meta Description', validators=[Optional(), Length(max=160)])
    meta_keywords = StringField('Meta Keywords', validators=[Optional(), Length(max=200)])
    published = BooleanField('Published')

class CategoryForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=50)])
    description = TextAreaField('Description', validators=[Optional()])

class TagForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=50)])

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(max=80)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = StringField('Password', validators=[Optional(), Length(min=6)])
    is_admin = BooleanField('Admin')

class PodcastForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description')
    audio_file = FileField('Audio File', validators=[FileAllowed(['mp3', 'wav', 'm4a', 'ogg'], 'Audio files only!')])
    duration = FloatField('Duration (minutes)')
    published_at = DateTimeField('Published At', format='%Y-%m-%dT%H:%M', validators=[Optional()])
