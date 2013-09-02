def foo():
       sum = 0
       for i in range(100):
              sum += i
       return sum
 
if __name__ == "__main__":
       import profile
       profile.run("foo()")
