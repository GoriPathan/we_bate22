from typing import List, Optional
from fastapi import HTTPException, Response, UploadFile, status, Depends, APIRouter, Form, File
from app import oauth2
import onesignal_sdk
from app.database import  get_db
from sqlalchemy.orm import Session
import boto3, datetime, string, random
from datetime import datetime
from app import oauth2, config
from app.models import models
from app.schemas import menu
from app import utils
import requests
from twilio.rest import Client

router= APIRouter(
    tags=['Create Menu']
)
S3_BUCKET_NAME = "codedeskstudio"

client_s3 = boto3.resource(
    service_name = config.settings.service_name,
    region_name = config.settings.region_name,
    aws_access_key_id = config.settings.aws_access_key_id,
    aws_secret_access_key = config.settings.aws_secret_access_key
)

@router.post('/create_menu', status_code=status.HTTP_200_OK)
def create_menu(name: str = Form(...),price: str = Form(...),menu_image: UploadFile = File(...),
                discription: str = Form(...),category_id: str = Form(...),
                db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_hotel)):
    
    check = db.query(models.Create_category).filter(models.Create_category.id == category_id).first()

    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This Id is not exist")

    new_menu: models.CreateMenu = models.CreateMenu()
    new_menu.menu_name = name
    new_menu.price = price
    new_menu.discription = discription
    new_menu.hotel_id = current_user.id
    new_menu.category_id = category_id

    bucket = client_s3.Bucket(S3_BUCKET_NAME)
    noow = str(datetime.now())
    bucket.upload_fileobj(menu_image.file, f"{noow}{menu_image.filename}")
    upload_url = f"https://{S3_BUCKET_NAME}.s3.ap-northeast-1.amazonaws.com/{noow}{menu_image.filename}"
    new_menu.menu_image = upload_url


    db.add(new_menu)
    db.commit()
    db.refresh(new_menu)

    responseDic = {'status': True, 'message' : 'offer created', 
                        'id': new_menu.id,
                        'name_offer': new_menu.menu_name,
                        'offer_on': new_menu.price,
                        'qr_number': new_menu.discription,
                        'qr_image': new_menu.menu_image,
                        'discription': new_menu.discription,
                        'category': check.category_name,
                        'hotel_name': current_user.name,
                        'hotel_image': current_user.hotel_image_url
                        }

    return responseDic

@router.put('/update_menu', status_code=status.HTTP_200_OK)
def update_menu(menu_id : str, update: menu.MenuUpdate ,db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_hotel)):
    
    updte = db.query(models.CreateMenu).filter(models.CreateMenu.id == menu_id)
    check = updte.first()

    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This menu not exist")
    
    check_category_id = db.query(models.Create_category).filter(models.Create_category.id == update.category_id).first()
    if not check_category_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This category is not found")
    
    updte.update(update.dict(), synchronize_session=False)
    db.commit()
    return {"Status": "Successfully update ofer"}

@router.delete('/delete_menu', status_code=status.HTTP_200_OK)
def delete_menu(menu_id: str,db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_hotel)):

    
    dell = db.query(models.CreateMenu).filter(models.CreateMenu.id == menu_id)
    check = dell.first()

    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This offer not exist")
    
    user_check = db.query(models.CreateMenu).filter(models.CreateMenu.hotel_id == current_user.id,
                                                      models.CreateMenu.id == menu_id).first()
    
    if not user_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You can't able to performed this action") 

    dell.delete(synchronize_session=False)
    db.commit()

    return {"Status": "Successfully deleted the offer"}