from typing import List, Optional
import uuid, os
from fastapi import HTTPException, Response, UploadFile, status, Depends, APIRouter, Form, File
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from app import oauth2
import onesignal_sdk
from app.database import  get_db
from sqlalchemy.orm import Session
import boto3, datetime, string, random
from datetime import datetime
from app import oauth2, config
from app.models import models
from app.schemas import offer
from app import utils
import requests
from twilio.rest import Client

router= APIRouter(
    tags=['Create Offer']
)

S3_BUCKET_NAME = "codedeskstudio"

client_s3 = boto3.resource(
    service_name = config.settings.service_name,
    region_name = config.settings.region_name,
    aws_access_key_id = config.settings.aws_access_key_id,
    aws_secret_access_key = config.settings.aws_secret_access_key
)




@router.post('/create_offer', status_code=status.HTTP_200_OK)
def create_offer(name: str = Form(...),offer_on: str = Form(...),qr_number: str = Form(...),qr_image: UploadFile = File(...),offer_image: UploadFile = File(...),
                 opening: str = Form(...),closing: str = Form(...),discription: str = Form(...),discount: str = Form(...),is_unlimited: bool = Form(...),
                 db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_hotel)):
    
    
    
    new_offer: models.Create_Offer = models.Create_Offer()
    new_offer.name = name
    new_offer.offer_on = offer_on
    new_offer.qr_number = qr_number
    new_offer.opening = opening
    new_offer.closing = closing
    new_offer.discription = discription
    new_offer.discount = discount
    new_offer.hotel_id = current_user.id
    new_offer.is_unlimited = is_unlimited

    bucket = client_s3.Bucket(S3_BUCKET_NAME)
    noow = str(datetime.now())
    bucket.upload_fileobj(qr_image.file, f"{noow}{qr_image.filename}")
    upload_url = f"https://{S3_BUCKET_NAME}.s3.ap-northeast-1.amazonaws.com/{noow}{qr_image.filename}"
    new_offer.qr_image = upload_url


    bucket.upload_fileobj(offer_image.file, f"{noow}{offer_image.filename}")
    upload_url_logo = f"https://{S3_BUCKET_NAME}.s3.ap-northeast-1.amazonaws.com/{noow}{offer_image.filename}"
    new_offer.offer_image = upload_url_logo

    db.add(new_offer)
    db.commit()
    db.refresh(new_offer)

    responseDic = {'status': True, 'message' : 'offer_created', 
                        'id': new_offer.id,
                        'name_offer': new_offer.name,
                        'offer_on': new_offer.offer_on,
                        'qr_number': new_offer.qr_number,
                        'qr_image': new_offer.qr_image,
                        'offer_image': new_offer.offer_image,
                        'opening': new_offer.opening,
                        'closing': new_offer.closing,
                        'discription': new_offer.discription,
                        'discount': new_offer.discount,
                        'is_unlimited': new_offer.is_unlimited,
                        'hotel_name': current_user.name,
                        'hotel_image': current_user.hotel_image_url
                        }

    return responseDic

@router.put('/update_offer', status_code=status.HTTP_200_OK)
def update_offer(offer_id : str, update: offer.OfferUpdate ,db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_hotel)):
    
    updte = db.query(models.Create_Offer).filter(models.Create_Offer.id == offer_id)
    check = updte.first()

    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This offer not exist")
    
    updte.update(update.dict(), synchronize_session=False)
    db.commit()
    return {"Status": "Successfully update ofer"}

@router.delete('/delete_offer', status_code=status.HTTP_200_OK)
def delete_offer(offer_id: str,db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_hotel)):

    
    dell = db.query(models.Create_Offer).filter(models.Create_Offer.id == offer_id)
    check = dell.first()

    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This offer not exist")
    
    user_check = db.query(models.Create_Offer).filter(models.Create_Offer.hotel_id == current_user.id,
                                                      models.Create_Offer.id == offer_id).first()
    
    if not user_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You can't able to performed this action") 

    dell.delete(synchronize_session=False)
    db.commit()

    return {"Status": "Successfully deleted the offer"}

