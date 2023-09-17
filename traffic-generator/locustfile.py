# This program will generate traffic for ACME Fitness Shop App. It simulates both Authenticated and Guest user scenarios. You can run this program either from Command line or from
# the web based UI. Refer to the "locust" documentation for further information.
from time import sleep
from locust import HttpUser, task, SequentialTaskSet, between
from random import randint
import random
import logging
import jwt

# List of users (pre-loaded into ACME Fitness shop)
users = ["eric", "phoebe", "dwight", "han", "elaine", "walter"]

# GuestUserBrowsing simulates traffic for a Guest User (Not logged in)
class UserBrowsing(SequentialTaskSet):
    def on_start(self):
        self.getProducts()
    def listCatalogItems(self):
        products = []
        response = self.client.get("/products")
        if response.ok:
            items = response.json()["data"]
            for item in items:
                products.append(item["id"])
        return products
    def getProductDetails(self, id):
        """Get details of a specific product"""
        details = {}
        response = self.client.get("/products/"+id)
        if response.ok:
            details = response.json()["data"]
            logging.debug("getProductDetails: " + str(details))
        return details
    def getProductImages(self,id):
        """Gets all three image URLs for a product"""
        details = self.getProductDetails(id)
        if details:
            for x in range(1, 4):
                self.client.get(details["imageUrl"+str(x)])
    def getProductName(self, id):
        name = ""
        details = self.getProductDetails(id)
        if details:
            name = details["name"]
        logging.debug("NAME: "+name+ " for id: "+id)
        return name

    @task
    def getProducts(self):
        logging.debug("User - Get Products")
        self.client.get("/products")
    @task(2)
    def getProduct(self):
        """Get details of a specific product"""
        logging.debug("User - Get a product")
        products = self.listCatalogItems()
        id = random.choice(products)
        response = self.client.get("/products/"+ id)
        if response.ok:
            product = response.json()
            logging.debug("Product info - " +  str(product))
    @task
    def getImages(self):
        """Get images of a random product"""
        logging.debug("User - Get images of random product")
        products = self.listCatalogItems()
        id = random.choice(products)
        self.getProductImages(id)
    @task(2)
    def index(self):
        self.client.get("/")

# AuthUserBrowsing simulates traffic for Authenticated Users (Logged in)
class AuthUserBrowsing(UserBrowsing):
    """
    AuthUserBrowsing extends the base UserBrowsing class as an authenticated user
    interacting with the cart and making orders
    """
    Order_Info = { "userid":"650267d4216ab38a2741b6d7",
                "firstname":"Eric",
                "lastname": "Cartman",
                "address":{
                    "street":"20 Riding Lane Av",
                    "city":"San Francisco",
                    "zip":"10201",
                    "state": "CA",
                    "country":"USA"},
                "email":"jblaze@marvel.com",
                "delivery":"FEDEX",
                "card":{
                    "type":"visa",
                    "number":"3498347979814323",
                    "expMonth":"12",
                    "expYear": "2029",
                    "ccv":"123"
                },
                "cart":[
                    {"itemid":"65026794a6d1d6ba5b90278d", "name":"redpants", "quantity":"1", "price":"101.25","shortDescription":"Test add to cart"},
                    {"itemid":"65026794a6d1d6ba5b90278e", "name":"bluepants", "quantity":"1", "price":"42.00","shortDescription":"Test add to cart"}
                ],
                "total":"143.25"}

    def on_start(self):
        self.login()
    def removeProductFromCart(self, userid, productid):
        """Removes a specific product from the cart by setting the quantity of the product to 0"""
        response = self.client.post("/cart/item/modify/"+userid, json={"itemid": productid, "quantity": 0})
        if response.ok:
            logging.debug("Auth User - Removed item: "+productid+" for user: "+userid)
        else:
            logging.warning("failed to remove cart entry. item: "+productid+" for user: "+userid)

    @task
    def login(self):
        """Login a random user"""
        user = random.choice(users)
        logging.debug("Auth User - Login user " + user)
        response = self.client.post("/login/", json={"username": user, "password":"vmware1!"})
        if response.ok:
            body = response.json()
            #self.user.userid = body["token"]
            #self.user.userid = body["access_token"]
            accesstoken = body["access_token"]
            decoded_data = jwt.decode(accesstoken, 'secret', verify=False, algorithms=["HS256"])
            #print("token: %s" % accesstoken)
            #decodedtoken = self.decode_user(accesstoken)
            self.user.userid = decoded_data["sub"]
            response2 = self.client.get("/users/" + self.user.userid)
            userdetails = response2.json()["data"]
            self.user.firstname = userdetails["firstname"]
            self.user.lastname = userdetails["lastname"]
            self.user.email = userdetails["email"]
            self.user.username = userdetails["username"]


    @task(2)
    def addToCart(self):
        """Randomly adds 1 or 2 of a random product to the cart"""
        products = self.listCatalogItems()
        productid = random.choice(products)
        if not self.user.userid:
            logging.warning("Not logged in, skipping 'Add to Cart'")
            return
        logging.debug("Add to Cart for user " + self.user.userid)
        details = self.getProductDetails(productid)
        cart = self.client.post("/cart/item/add/" + self.user.userid, json={
                  "name": details["name"],
                  "price": details["price"],
                  "shortDescription": "Test add to cart",
                  "quantity": random.randint(1,2),
                  "itemid": productid
                })
    @task
    def removeFromCart(self):
        """Remove a random product from the cart. Helps prevent the cart from overflowing"""
        products = self.listCatalogItems()
        productid = random.choice(products)
        self.removeProductFromCart(self.user.userid, productid)
    @task
    def checkout(self):
        if not self.user.userid:
            logging.warning("Not logged in, skipping 'Add to Checkout'")
            return
        userCart = self.client.get("/cart/items/" + self.user.userid).json()
        cartitems = userCart["cart"]
        total = 0
        for item in cartitems:
            total = total + item["price"]
        #print(userCart)
        deliverychoices = ["FEDEX", "UPS", "DHL"]
        r_delivery = random.choice(deliverychoices)
        cctypechoices = ["AMEX", "VISA", "MASTERCARD"]
        r_cctype = random.choice(cctypechoices)
        cc = ''
        for i in range(16):
            cc = cc + str(randint(0,9))
        ccmo = str(randint(1,12))
        ccyr = str(randint(2025,2035))
        ccv = str(randint(100,999))
        This_Order_Info = { "userid":self.user.userid,
                "firstname":self.user.firstname,
                "lastname":self.user.lastname,
                "address":{
                    "street":"20 Riding Lane Av",
                    "city":"San Francisco",
                    "zip":"10201",
                    "state": "CA",
                    "country":"USA"},
                "email":self.user.email,
                "delivery":r_delivery,
                "card":{
                    "type":r_cctype,
                    "number":cc,
                    "expMonth":ccmo,
                    "expYear":ccyr,
                    "ccv":ccv
                },
                "cart":cartitems,
                "total":total }
        #print(This_Order_Info)
        order = self.client.post("/order/add/"+ self.user.userid, json=This_Order_Info)
class UserBehavior(SequentialTaskSet):
    tasks = [AuthUserBrowsing, UserBrowsing]
class WebSiteUser(HttpUser):
    sleep(3)  # Sleep on start of a user incase the target app isn't completely accessible yet.
    tasks = [UserBehavior]
    userid = ""
    wait_time = between(0.5, 3)
