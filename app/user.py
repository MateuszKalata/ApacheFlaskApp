from app.address import *

class User:

    def __init__(self, login: str, fname: str, lname: str, birthDate, phone: str, address: Address):
        self.login = login
        self.fname = fname
        self.lname = lname
        self.bithDate = birthDate
        self.phone = phone
        self.address = address
        
    def user_to_dict(self):
        u = {'login': self.login,
            'fname': self.fname,
            'lname': self.lname,
            'bithDate': self.bithDate,
            'phone': self.phone,
            'address': self.address.address_to_dict()
            }
        return u

