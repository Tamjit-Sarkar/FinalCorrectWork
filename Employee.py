from os import access


class Employee:
    def __init__(self,id,name,salary):
        self.__id = id
        self.__name = name
        self.__salary = salary


    def bonus(self):
        self.__salary = (self.__salary * 0.1) + self.__salary
        return self.__salary


class support(Employee):
    def __init__(self,id,name,salary,access):
        super().__init__(id,name,salary)
        self.__access = access

    def show(self):
        if self.__access == 'yes':
            return 'allowed'
        else:
            return 'not allowed'


P1 = Employee(100,'tam',1000)
S1 = support(200,'tamu',20000,'yes')

print(S1.bonus())
print(S1.show())
