from flask import Blueprint, request, make_response
from sqlalchemy import create_engine
from collections import OrderedDict
from datetime import date
from . import controller

bp = Blueprint('pictures',__name__,url_prefix='/')

@bp.post("/image_tags")
def image_tags():
    engine = controller.select_or_create_database()
    
    min_confidence = request.args.get("min_confidence", 80)
    print(f"Min. confidence: {min_confidence}")
    if not request.is_json:
        return make_response("Body must be in json format", 400)
    image_json = request.json
    image_base64 = image_json["data"]

    # Función para subir la imagen y tener una url publica
    upload_info = controller.upload_image_cloud(image_base64)
    
    # Función para hacer la operación de tagging
    tags_json = controller.get_image_tags(upload_info, min_confidence=int(min_confidence))

    # Función para eliminar la imagen de la primera página
    controller.delete_image_cloud(upload_info.file_id)

    # Cración de un ID unico para la img y guardarla en carpeta
    image_uuid = controller.save_bin_image_folder(image_base64)
    
    # Funciones para la fecha y el size de la imagen
    image_date = controller.create_image_date()
    image_size = controller.get_image_size_base64(image_base64)

    # Funciones para añadir a las tablas
    controller.add_row_pictures(image_uuid=image_uuid, image_date=image_date, engine=engine)
    controller.add_row_tags(tags=tags_json, image_uuid=image_uuid, image_date=image_date, engine=engine)
    
    return {
        "id":image_uuid,
        "size":image_size,
        "date":image_date,
        "tags":tags_json,
        "data":image_base64
    }


@bp.get("/get_images")
def get_images():    

    min_date = date.fromisoformat(request.args.get("min_date", '1000-01-01'))
    max_date = date.fromisoformat(request.args.get("max_date", '9999-12-31'))

    # Convertir strings
    min_date_str = min_date.isoformat()
    max_date_str = max_date.isoformat()

    tags_string = request.args.get("tags_list"," ")

    tags_list = controller.tags_list_def(tags_string)
    print(f"Extracting data considering the tags {tags_list} between {min_date_str} and {max_date_str}...")

    list_images_filtered = controller.images_id_filter(min_date, max_date, tags_list)

    output_images_list = controller.get_output_images_list(list_images_filtered)

    return output_images_list


@bp.get("/download_image/<image_id>")
def download_image(image_id):
    engine = create_engine("mysql+pymysql://mbit:mbit@db/Pictures")
    image_size = controller.get_image_size(image_id=image_id, engine=engine)
    image_date = controller.get_image_date (image_id=image_id, engine=engine)
    image_tags = controller.get_image_tags (image_id=image_id, engine=engine)
    image_base64 = controller.get_image_base64(image_id=image_id, engine=engine)
    controller.download_image_api(image_id = image_id, engine = engine)

    return OrderedDict([
        ("id", image_id),
        ("size", image_size),
        ("date", image_date),
        ("tags", image_tags),
        ("data", image_base64)
    ])


@bp.get("/get_tags")
def get_tags():
    engine = create_engine("mysql+pymysql://mbit:mbit@db/Pictures")
    min_date = date.fromisoformat(request.args.get("min_date", '1000-01-01'))
    max_date = date.fromisoformat(request.args.get("max_date", '9999-12-31'))

    # Convertir strings
    min_date_str = min_date.isoformat()
    max_date_str = max_date.isoformat()

    tag_list = controller.get_tags_info(engine,min_date_str, max_date_str)

    return tag_list