from . import models
import pandas as pd
from flask import Flask, make_response,request
from sqlalchemy import create_engine, text
import requests
import base64
import json
from imagekitio import ImageKit
from PIL import Image
from io import BytesIO
import string    
from datetime import datetime, date
import uuid
import datetime
from collections import OrderedDict
import os


# Funcion para subir la imagen a ImageKit
def upload_image_cloud(image_base64):
    
    imagekit = ImageKit(
        public_key= os.environ['imagekit_api_key'],
        private_key= os.environ['imagekit_private_key'],
        url_endpoint = os.environ['imagekit_url_endpoint']
    )

    print("Subiendo la imagen...")

    # Subir la imagen
    upload_info = imagekit.upload(file=image_base64, file_name="my_file_name.jpg")
    
    print(f"Image {upload_info.file_id} succesfully uploaded to Imagekit.\n")

    return upload_info


# Funcion para subir la imagen a Imagga y analizarla con IA para sacar los Tags y Confidence
def get_image_tags(upload_info, min_confidence=80):

    api_key = os.environ['imagga_api_key']
    api_secret = os.environ['imagga_api_secret']
    
    print(f"Procesando imagen {upload_info.file_id} en Imagga...")
    response = requests.get(f"https://api.imagga.com/v2/tags?image_url={upload_info.url}", auth=(api_key, api_secret))
    tags = [
        {
            "tag": t["tag"]["en"],
            "confidence": t["confidence"]
        }
        for t in response.json()["result"]["tags"]
        if t["confidence"] > min_confidence
    ]

    print(f"Tags succesfully generated with a confidence higher than {min_confidence}: {tags}\n")

    return tags


# Funcion para borrar una imagen en Imagekit
def delete_image_cloud(file_id):
  
    imagekit = ImageKit(
        public_key= os.environ['imagekit_api_key'],
        private_key= os.environ['imagekit_private_key'],
        url_endpoint = os.environ['imagekit_url_endpoint']
    )

    # Borrar una imagen
    delete = imagekit.delete_file(file_id=file_id)

    print(f"Imagen {file_id} correctamente borrada.\n")

    return None

# Funcion para guardar la imagen analizada en Imagga 
def save_bin_image_folder(image_base64):

    # Crea un objetp de imagen desde un base64 encoded
    image_data = BytesIO(base64.b64decode(image_base64))
    image = Image.open(image_data)
    image_uuid = str(uuid.uuid4())
    print(f"Guardando la imagen {image_uuid}...")
    # Guardar como JPG en la carpeta 
    save_path = f"/app/images_db/{image_uuid}.jpg" 
    image.save(save_path, "Imagenes")

    print(f"Imagen {image_uuid} correctamente guardada em {save_path}.")
    return image_uuid


# Funcion para añadir los datos a la BBDD de Pictures
def add_row_pictures(image_uuid, image_date, engine): 

    pictures_json = {
        "id":image_uuid,
        "path":f"/app/images_db/{image_uuid}.jpg",
        "date":image_date
    }
    df_pictures = pd.DataFrame([pictures_json])

    print("Añadiendo la nueva fila a la tabla 'pictures'...")
    df_pictures.to_sql(name='pictures', con=engine, if_exists='append', index=False)
    print("Fila añadida correctamente.")
    return None

# Funcion para añadir los datos a la BBDD de Tags
def add_row_tags(tags, image_uuid, image_date, engine): 

    if tags:  
        df_tags = (
            pd.DataFrame.from_records(tags)
            .assign(
                picture_id = image_uuid
            )
            .assign(
                date = image_date
            )
            [["tag", "picture_id","confidence","date"]]
        )
        print("Añadiendo la nueva fila a la tabla 'tags'...")
        df_tags.to_sql(name='tags',
                        con=engine,
                        if_exists='append',
                        index=False)
    
    else:
        json_tags = {
            "tag":"NA",
            "picture_id":image_uuid,
            "confidence":0,
            "date":image_date
        }

        df_tags = (
            pd.DataFrame([json_tags])
        )

        df_tags.to_sql(name='tags',
                        con=engine,
                        if_exists='append',
                        index=False)

    print("Nueva fila añadida correctamente a la tabla'tags'.")
    return None


def create_image_date():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_image_size_base64(image_base64):
    return f"{round(len(base64.b64decode(image_base64))/1024, 2)}KB"

def select_or_create_database():
    
    engine = create_engine('mysql+pymysql://mbit:mbit@db:3306')

    # Create the 'Pictures' database if it doesn't exist
    with engine.begin() as connection:
        # Create a DDL statement to create the database
        create_db_statement = text('CREATE DATABASE IF NOT EXISTS Pictures')

        # Execute the DDL statement
        connection.execute(create_db_statement)

    # Connect to the 'Pictures' database
    engine = create_engine('mysql+pymysql://mbit:mbit@db:3306/Pictures')

    # Execute SQL statements
    with engine.begin() as connection:
        # Create 'pictures' table
        create_pictures_table = text(models.query_create_table_pictures)
        connection.execute(create_pictures_table)

        # Create 'tags' table
        create_tags_table = text(models.query_create_table_tags)
        connection.execute(create_tags_table)
    
    return engine


# Funcion que extrae las tags asociadas a una imagen
def get_image_date (image_id, engine):
    
    engine = create_engine("mysql+pymysql://mbit:mbit@db/Pictures")
    query = models.query_select_all_tags

    df_tags_image = (
        pd.read_sql_query(query, con=engine)
        .groupby(["picture_id", "tag", "confidence", "date"]).count()
        .loc[image_id]
        .reset_index()
    )

    return df_tags_image["date"].loc[0]


# Funcion para calcular el size de una imagen
def get_image_size(image_id, engine):
  
    engine = create_engine("mysql+pymysql://mbit:mbit@db/Pictures")
    query = models.query_select_all_pictures
    df_pictures = pd.read_sql_query(query, con=engine)
    file_path = (
        df_pictures
        .loc[df_pictures["id"]==image_id]
        ["path"]
        .values[0]
    )
    try:
        with open(file_path, "rb") as file:
            image_bin = file.read()

        image_base64 = (
            base64.b64encode(image_bin)
            .decode()
        )

        image_size = f"{round(len(base64.b64decode(image_base64))/1024, 2)}KB"

        return image_size
    
    except:
        return "No disponible la información"


# Extracción de las tags asociadas a una imagen
def get_image_tags (image_id, engine):
   
    engine = create_engine("mysql+pymysql://mbit:mbit@db/Pictures")
    query = models.query_select_all_tags

    df_tags_image = (
        pd.read_sql_query(query, con=engine)
        .groupby(["picture_id", "tag", "confidence", "date"]).count()
        .loc[image_id]
        .reset_index()
    )

    list_tags = []
    for index, row in df_tags_image.iterrows():
        test_image_dict = {
            "tag":row["tag"],
            "confidence":row["confidence"]
        }
        list_tags.append(test_image_dict)
    return list_tags


app = Flask(__name__)

@app.get("/get_images")
def get_images():    
    engine = create_engine("mysql+pymysql://mbit:mbit@db/Pictures")

    min_date = date.fromisoformat(request.args.get("min_date", '1000-01-01'))
    max_date = date.fromisoformat(request.args.get("max_date", '9999-12-31'))

    min_date_str = min_date.isoformat()
    max_date_str = max_date.isoformat()

    tags_string = request.args.get("tags_list"," ")

    if tags_string != " ":
        tags_list = tags_string.split(",")

    else:
        query = models.query_select_all_tags

        tags_list = (
            pd.read_sql_query(query, con=engine)
            ['tag']
            .drop_duplicates()
            .to_list()
            )
    print(f"Extrayendo datos considerando los tags {tags_list} entre {min_date} y {max_date}...")

    query = f"""SELECT  id, 
                        path, 
                        CAST(date AS date) AS dates
                FROM pictures
                WHERE date BETWEEN '{min_date_str}' AND '{max_date_str}'"""

    df_pictures = pd.read_sql_query(query, con=engine)

    df_tags_filtered = pd.DataFrame()
    for tag in tags_list:
        query = f"""SELECT * 
                FROM tags
                WHERE tag = '{tag}'
                ORDER BY picture_id"""
        df_tags_filtered = pd.concat([df_tags_filtered, pd.read_sql_query(query, con=engine)],
                            axis=0)
    df_tags_filtered = df_tags_filtered.reset_index(drop = True)

    df_tags_filtered[df_tags_filtered["tag"]==len(tags_list)]["picture_id"].tolist()
    df_tag_pictures = (
        df_tags_filtered
        .merge(df_pictures, how = "inner",
                    left_on="picture_id",
                    right_on="id")
        [['id','tag','confidence','date','path']]
        .sort_values(by="id")    
    )

    df_tag_pictures = (
        df_tag_pictures
        .groupby("id")
        .count()
        [["tag"]]
        .reset_index()
    )

    list_images_filtered = (
        df_tag_pictures
        [df_tag_pictures["tag"]==len(tags_list)]
        ["id"]
        .to_list()
    )
    list_images_filtered

    output_images_list = []
    for image_id in list_images_filtered:
        image_size = get_image_size(image_id=image_id, engine=engine)
        image_date = get_image_date (image_id=image_id, engine=engine)
        image_tags = get_image_tags(image_id, engine=engine)

        output_images_list_partial = {
            "id":image_id,
            "size":image_size,
            "date":image_date,
            "tags":image_tags
        }
        output_images_list.append(output_images_list_partial)
        print(f"{output_images_list_partial}\n")

    return output_images_list


def tags_list_def(tags_string):
    engine = create_engine("mysql+pymysql://mbit:mbit@db/Pictures")
    if tags_string != " ":
        tags_list = tags_string.split(",")

    else:
        query = models.query_select_all_tags

        tags_list = (
            pd.read_sql_query(query, con=engine)
            ['tag']
            .drop_duplicates()
            .to_list()
            )
    return tags_list


def images_id_filter(min_date_str, max_date_str, tags_list):
    engine = create_engine("mysql+pymysql://mbit:mbit@db/Pictures")
    query = f"""SELECT  id, 
                path, 
                CAST(date AS date) AS dates
                FROM pictures
                WHERE date BETWEEN '{min_date_str}' AND '{max_date_str}'"""

    df_pictures = pd.read_sql_query(query, con=engine)

    df_tags_filtered = pd.DataFrame()
    for tag in tags_list:
        query = f"""SELECT * 
                FROM tags
                WHERE tag = '{tag}'
                ORDER BY picture_id"""
        df_tags_filtered = pd.concat([df_tags_filtered, pd.read_sql_query(query, con=engine)],
                            axis=0)
    df_tags_filtered = df_tags_filtered.reset_index(drop = True)

    df_tags_filtered[df_tags_filtered["tag"]==len(tags_list)]["picture_id"].tolist()
    df_tag_pictures = (
        df_tags_filtered
        .merge(df_pictures, how = "inner",
                    left_on="picture_id",
                    right_on="id")
        [['id','tag','confidence','date','path']]
        .sort_values(by="id")    
    )

    df_tag_pictures = (
        df_tag_pictures
        .groupby("id")
        .count()
        [["tag"]]
        .reset_index()
    )

    list_images_filtered = (
        df_tag_pictures
        [df_tag_pictures["tag"]==len(tags_list)]
        ["id"]
        .to_list()
    )
    return list_images_filtered


def get_output_images_list(list_images_filtered):
    
    output_images_list = []
    for image_id in list_images_filtered:
        engine = create_engine("mysql+pymysql://mbit:mbit@db/Pictures")
        image_size = get_image_size(image_id=image_id, engine=engine)
        image_date = get_image_date (image_id=image_id, engine=engine)
        image_tags = get_image_tags(image_id, engine=engine)

        output_images_list_partial = {
            "id":image_id,
            "size":image_size,
            "date":image_date,
            "tags":image_tags
        }
        output_images_list.append(output_images_list_partial)
        print(f"{output_images_list_partial}\n")

    return output_images_list


def download_image_api(image_id, engine):
    
    query = models.query_select_all_pictures
    df_pictures = pd.read_sql_query(query, con=engine)
    file_path = (
        df_pictures
        .loc[df_pictures["id"]==image_id]
        ["path"]
        .values[0]
    )
    print(f"Guardando el archivo en {file_path}...")
    try:
        with open(file_path, "rb") as file:
            image_bin = file.read()

        save_path = f"../tmp/{image_id}.jpg" # Sustituir por el volumen
        with open(save_path, "wb") as save_file:
            save_file.write(image_bin)
        
        print(f"Archivo guardado en {save_path}")
    except:
        print("Error. No se pudo guardar.")
    return None


def get_image_base64(image_id, engine):

    query = models.query_select_all_pictures
    df_pictures = pd.read_sql_query(query, con=engine)
    file_path = (
        df_pictures
        .loc[df_pictures["id"]==image_id]
        ["path"]
        .values[0]
    )
    try:
        with open(file_path, "rb") as file:
            image_bin = file.read()

        image_base64 = (
            base64.b64encode(image_bin)
            .decode()
        )
        return image_base64

    except:
        print("Imagen no disponible")
        return None


def get_tags_info(engine, min_date_str, max_date_str):
   
    query = f"""SELECT  tag, 
                    picture_id,
                    confidence,
                    CAST(date AS date) AS dates
            FROM tags
            WHERE date BETWEEN '{min_date_str}' AND '{max_date_str}'"""

    tag_list = []
    df_pictures = pd.read_sql_query(query, con=engine)
    print(df_pictures)
    for tag in list(df_pictures.tag.unique()):
        df_picture_tags = (
            df_pictures
            .groupby(["tag", "picture_id", "confidence", "dates"])
            .count()
            .loc[tag]
            .reset_index()
        )
        n_images = int(df_picture_tags.size / len(df_picture_tags.columns))
        min_confidence = df_picture_tags.confidence.min()
        max_confidence = df_picture_tags.confidence.max()
        mean_confidence = df_picture_tags.confidence.mean()
        tag_info = {
            "tag": tag,
            "n_images": n_images,
            "min_confidence": min_confidence,
            "max_confidence": max_confidence,
            "mean_confidence": mean_confidence
        }
        tag_list.append(tag_info)
    return tag_list
