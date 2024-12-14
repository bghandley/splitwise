# Spirit of the Deal Website

A spiritual business growth platform with an integrated CMS and podcast management system.

## Project Structure

```
/
├── frontend/           # Frontend static files
├── cms/               # Content Management System (Flask)
│   ├── static/        # Static files for CMS
│   ├── templates/     # HTML templates
│   └── uploads/       # User uploaded content
├── index.html         # Main website
├── podcast.html       # Podcast page
└── styles.css         # Global styles
```

## Setup and Installation

### Frontend
The frontend is a static website that can be served from any web server.

### CMS Backend
1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
cd cms
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
# Create .env file in cms directory
SECRET_KEY=your_secret_key
DATABASE_URL=sqlite:///cms.db
```

4. Initialize the database:
```bash
python init_db.py
```

5. Run the development server:
```bash
python app.py
```

## Deployment

### Frontend Deployment
The frontend can be deployed to any static hosting service:
- Netlify
- GitHub Pages
- Amazon S3
- Firebase Hosting

### Backend Deployment
The CMS can be deployed to:
- Heroku
- PythonAnywhere
- DigitalOcean
- AWS Elastic Beanstalk

## Features

- Responsive design
- Content Management System
- Blog post management
- Podcast episode management
- User authentication
- Audio file processing
- Automatic transcription
- SEO optimization

## Environment Variables

Required environment variables for the CMS:
- `SECRET_KEY`: Flask secret key
- `DATABASE_URL`: Database connection URL

## License

MIT License
