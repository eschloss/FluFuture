
def orderList(p):
    for n, v in enumerate(p):
        if type(v) is dict:
            p[n] = orderDict(v)
        elif type(v) is list:
            p[n] = orderList(v)
    return p

def orderDict(p):
    for k in p.keys():
        v = p[k]
        if type(v) is dict:
            p[k] = orderDict(v)
        if type(v) is list:
            p[k] = orderList(v)
    p = sorted(p.items())
    return p

def getData(csv=False):
    
    import ssl 
    import pymongo
    from django.conf import settings 
    import random 
    import os
    import re
    from bson.json_util import dumps
    
    
    """ GMOJI
    client = pymongo.MongoClient(random.choice(getattr(settings, "MONGODB_HOST", None)),
                                ssl=settings.MONGODB_SSL, 
                                ssl_cert_reqs=ssl.CERT_NONE, 
                                username=settings.MONGODB_USER, 
                                password=settings.MONGODB_PWD)
    """
    
    ###LIVERSMART LOGIN
    client = pymongo.MongoClient(random.choice(getattr(settings, "MONGODB_HOST", None)),
                                          ssl=True
                                          )
    
    db_names = client.database_names()
    random.shuffle(db_names)
    
    if csv:
        f= open("sduhf2879ggfsyfjkshsdfbv.csv","w+")
    
    for db_name in db_names:
        db = client[db_name]
        col = db['funf']
        
        if not csv:
            f= open("%s.txt" % db_name,"w+")
            f.write("[")
        for i in col.find():
            if csv:
                p = str(orderDict(i))
                f.write("%s, %s\n" % (db_name, re.sub(r"u'|'|\{|\}|\[|\]|\(|\)", '', p)))
            else:
                f.write("%s," % dumps(i))
        
        if not csv:
            f.write("{}]")
            f.close()
        
            os.system("curl --upload-file ./%s.txt https://transfer.sh/%s.txt" % (db_name, db_name))
            print ""
    
    
    if csv:
        os.system("curl --upload-file ./sduhf2879ggfsyfjkshsdfbv.csv https://transfer.sh/sduhf2879ggfsyfjkshsdfbv.csv")
    
    return client, db_names
