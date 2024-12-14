from flask import Blueprint, jsonify
from flasgger import Swagger, swag_from

api_docs = Blueprint('api_docs', __name__)

# Initialize Swagger
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/docs"
}

swagger_template = {
    "info": {
        "title": "Spirit of the Deal CMS API",
        "description": "API documentation for the Spirit of the Deal CMS",
        "version": "1.0.0",
        "contact": {
            "name": "API Support",
            "url": "https://spiritofthedeal.com/support",
        }
    },
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Authorization header using the Bearer scheme. Example: \"Bearer {token}\""
        }
    },
    "security": [
        {
            "Bearer": []
        }
    ]
}

# API endpoint documentation
@api_docs.route('/api/posts', methods=['GET'])
@swag_from({
    'tags': ['Posts'],
    'summary': 'Get blog posts',
    'parameters': [
        {
            'name': 'page',
            'in': 'query',
            'type': 'integer',
            'default': 1,
            'description': 'Page number'
        },
        {
            'name': 'limit',
            'in': 'query',
            'type': 'integer',
            'default': 10,
            'description': 'Number of posts per page'
        },
        {
            'name': 'category',
            'in': 'query',
            'type': 'string',
            'description': 'Filter by category slug'
        },
        {
            'name': 'tag',
            'in': 'query',
            'type': 'string',
            'description': 'Filter by tag slug'
        },
        {
            'name': 'search',
            'in': 'query',
            'type': 'string',
            'description': 'Search query'
        }
    ],
    'responses': {
        200: {
            'description': 'List of blog posts',
            'schema': {
                'type': 'object',
                'properties': {
                    'data': {
                        'type': 'array',
                        'items': {
                            '$ref': '#/definitions/Post'
                        }
                    },
                    'meta': {
                        'type': 'object',
                        'properties': {
                            'total': {'type': 'integer'},
                            'page': {'type': 'integer'},
                            'pages': {'type': 'integer'}
                        }
                    }
                }
            }
        }
    }
})
def get_posts():
    """Get a list of blog posts"""
    pass

@api_docs.route('/api/post/<slug>', methods=['GET'])
@swag_from({
    'tags': ['Posts'],
    'summary': 'Get a single blog post',
    'parameters': [
        {
            'name': 'slug',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': 'Post slug'
        }
    ],
    'responses': {
        200: {
            'description': 'Blog post details',
            'schema': {
                '$ref': '#/definitions/Post'
            }
        },
        404: {
            'description': 'Post not found'
        }
    }
})
def get_post(slug):
    """Get a single blog post by slug"""
    pass

@api_docs.route('/api/categories', methods=['GET'])
@swag_from({
    'tags': ['Categories'],
    'summary': 'Get all categories',
    'responses': {
        200: {
            'description': 'List of categories',
            'schema': {
                'type': 'array',
                'items': {
                    '$ref': '#/definitions/Category'
                }
            }
        }
    }
})
def get_categories():
    """Get all categories"""
    pass

@api_docs.route('/api/tags', methods=['GET'])
@swag_from({
    'tags': ['Tags'],
    'summary': 'Get all tags',
    'responses': {
        200: {
            'description': 'List of tags',
            'schema': {
                'type': 'array',
                'items': {
                    '$ref': '#/definitions/Tag'
                }
            }
        }
    }
})
def get_tags():
    """Get all tags"""
    pass

# Model definitions
definitions = {
    'Post': {
        'type': 'object',
        'properties': {
            'id': {'type': 'integer'},
            'title': {'type': 'string'},
            'slug': {'type': 'string'},
            'content': {'type': 'string'},
            'excerpt': {'type': 'string'},
            'featured_image': {'type': 'string'},
            'author': {'$ref': '#/definitions/User'},
            'category': {'$ref': '#/definitions/Category'},
            'tags': {
                'type': 'array',
                'items': {'$ref': '#/definitions/Tag'}
            },
            'created_at': {'type': 'string', 'format': 'date-time'},
            'updated_at': {'type': 'string', 'format': 'date-time'},
            'published_at': {'type': 'string', 'format': 'date-time'},
            'status': {'type': 'string', 'enum': ['draft', 'published']},
            'views': {'type': 'integer'},
            'shares': {'type': 'integer'},
            'seo': {
                'type': 'object',
                'properties': {
                    'title': {'type': 'string'},
                    'description': {'type': 'string'},
                    'keywords': {'type': 'string'}
                }
            }
        }
    },
    'User': {
        'type': 'object',
        'properties': {
            'id': {'type': 'integer'},
            'username': {'type': 'string'},
            'email': {'type': 'string'},
            'is_admin': {'type': 'boolean'}
        }
    },
    'Category': {
        'type': 'object',
        'properties': {
            'id': {'type': 'integer'},
            'name': {'type': 'string'},
            'slug': {'type': 'string'},
            'description': {'type': 'string'}
        }
    },
    'Tag': {
        'type': 'object',
        'properties': {
            'id': {'type': 'integer'},
            'name': {'type': 'string'},
            'slug': {'type': 'string'}
        }
    }
}
