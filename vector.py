
import math
class Vector():
    def __init__(self, vals):
        
        self.vals=vals
        self.n=len(vals)

    def __sub__(self, other):
        if self.n!=other.n:
            return None
        return Vector([self.vals[i]-other.vals[i] for i in range(self.n)])
    def __add__(self, other):
        if self.n!=other.n:
            return None
        return Vector([self.vals[i]+other.vals[i] for i in range(self.n)])

    def dist(self, other):
        if self.n!=other.n:
            return None

        dist=0

        for i in range(self.n):
            dist+=(self.vals[i]-other.vals[i])**2
        return math.sqrt(dist)
    def dot(self, other):
        return sum(self.vals[i] * other.vals[i] for i in range(self.n))
    def __mul__(self, other):
        if isinstance(other, Vector):
            return Vector([self.vals[i]*other.vals[i] for i in range(self.n)])

        return Vector([val*other for val in self.vals])
    def __truediv__(self, other):
        return Vector([val/other for val in self.vals])
    def __abs__(self):
        dist=0

        for i in range(self.n):
            dist+=self.vals[i]**2
        return math.sqrt(dist)

    def __repr__(self):

        ans=""
        for i in range(self.n):
            ans+=f"{round(self.vals[i],2)} "
        return ans
    