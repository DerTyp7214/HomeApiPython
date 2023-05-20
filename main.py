#!/usr/bin/env python3

if __name__ == "__main__":
    import uvicorn
    from app import app, consts
    from app.sql_app.database import Base, engine
    
    Base.metadata.create_all(bind=engine)

    uvicorn.run(app, host="0.0.0.0", port=consts.port)
