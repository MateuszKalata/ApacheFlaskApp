class Address:
    
    def __init__(self, street: str, number: str, postalCode: str, city: str, country: str):
        self.street = street
        self.number = number
        self.postalCode = postalCode
        self.city = city
        self.country = country

    def get_street(self):
        return self.street + self.number

    def get_city(self):
        return self.city

    def get_postal_code(self):
        return self.postalCode

    def get_address_str(self):
        result = "\t\t{} {}".format(self.street, self.number)
        result += "\n\t\t{} {}".format(self.postalCode, self.city)
        result += "\n\t\t{}".format(self.country)
        return result

    def address_to_dict(self):
        a = {"street": self.street,"number": self.number,"postalCode": self.postalCode, "city": self.city, "country": self.country}
        return a
    