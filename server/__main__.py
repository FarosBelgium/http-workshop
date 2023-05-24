from threadedserver import ThreadedServer

if __name__ == "__main__":
    # Creates a ThreadedServer-object and calls the method that listens to the incoming client requests
    ThreadedServer().listen()
