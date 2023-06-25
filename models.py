from . import db
import uuid
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Picture(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=str(uuid.uuid4()))
    path = db.Column(db.String(255))
    date = db.Column(db.String(19))  # Formato: YYYY-MM-DD HH:MM:SS

    def __repr__(self):
        return f"<Picture {self.id}>"
    
    @staticmethod
    def query_select_all_pictures():
        return db.session.query(Picture).all()


class Tag(db.Model):
    tag = db.Column(db.String(32), primary_key=True)
    picture_id = db.Column(db.String(36), db.ForeignKey('picture.id'), primary_key=True)
    confidence = db.Column(db.Float)
    date = db.Column(db.String(19))  # Formato: YYYY-MM-DD HH:MM:SS

    picture = db.relationship('Picture', backref=db.backref('tags', lazy=True))

    def __repr__(self):
        return f"<Tag {self.tag} - Picture {self.picture_id}>"
    
    @staticmethod

    def query_select_all_tags():
        return db.session.query(Tag).all()

    
db.create_all()