import base64
import secrets
import json
import requests
from nacl.public import PrivateKey, SealedBox,  PublicKey
from nacl.pwhash import argon2id
import datetime
import boto3

def get_messages(bucket, private_key, last_seen):
    seal = SealedBox(private_key)
    s3 = boto3.client('s3', region_name='il-central-1')
    while True:
        response = s3.list_objects_v2(Bucket=bucket, 
            Prefix='ids/',
            StartAfter=last_seen or 'ids/')
        files = response.get('Contents', [])
        if(len(files) == 0):
            break
        for file in files:
            encrypted_id_file = s3.get_object(Bucket=bucket, Key=file['Key'])
            last_seen = file['Key']
            lines = encrypted_id_file['Body'].read().decode('ascii').splitlines()
            for line in lines:
                id = base64.urlsafe_b64decode(line)
                try:
                    file_name = seal.decrypt(id)
                    print(file_name)
                except:
                    pass # expected
            

    return last_seen

key = PrivateKey(base64.b64decode('Iei28jYsIl5E/Kks9BzGeg/36CKsrojEh65IUE2eNvA='))
#print(base64.urlsafe_b64encode(bytes(key.public_key)))
msgs = get_messages('cloud-dead-drop-c151295', key, None)

# s3 = boto3.client('s3', region_name='il-central-1')

# seed_phrase = b"Justify Aim Dart Utensil Tartness Grout"
# seed = argon2id.kdf(32, seed_phrase, b"salty journalist")
# skbob = PrivateKey.from_seed(seed)
# print(base64.b64encode(bytes(skbob)))
#print(base64.urlsafe_b64encode(bytes(skbob.public_key)))

# journalist_pk = base64.urlsafe_b64decode(b'GVT0GzjFRvMxcDh9c6jpmXkHoGB5KoIp9vyU3RozT2A=')
# seal = SealedBox(PublicKey(journalist_pk))
# encrypted = seal.encrypt(secrets.token_bytes(80))

# key = PrivateKey(base64.b64decode('Iei28jYsIl5E/Kks9BzGeg/36CKsrojEh65IUE2eNvA='))
# unseal = SealedBox(key)
# unseal.decrypt(encrypted)

# print(len(encrypted))
# print(base64.urlsafe_b64encode(encrypted))
# print(len(base64.urlsafe_b64encode(encrypted)))

# gen_upload_url =    "https://ya1nznmd5d.execute-api.il-central-1.amazonaws.com/stage/upload-url"
# register_id =       "https://ya1nznmd5d.execute-api.il-central-1.amazonaws.com/stage/register-id"

# upload_details = json.loads(requests.get(gen_upload_url).text)
# msg = b'Soft kitten' #input("Enter message: ")
# journalist_pk = base64.urlsafe_b64decode(b'GVT0GzjFRvMxcDh9c6jpmXkHoGB5KoIp9vyU3RozT2A=')
# seal = SealedBox(PublicKey(journalist_pk))
# encrypted_msg = seal.encrypt(msg)
# requests.put(upload_details['url'], data=encrypted_msg).raise_for_status()
# id = base64.urlsafe_b64decode(upload_details['id'] + '=')
# encrypted_id = seal.encrypt(id)
# requests.put(register_id, data=encrypted_id).raise_for_status()


# message = base64.urlsafe_b64decode(id + '=')
# print(len(message))

# encrypted = bob_box.encrypt(message)
# print(len(encrypted))

# # id = secrets.token_bytes(32)
# # print(id)
# # print(base64.urlsafe_b64encode(id))

# print(base64.urlsafe_b64encode(encrypted))
# print(len(base64.urlsafe_b64encode(encrypted)))

# print(datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='microseconds'))