# backend

FastAPI service for task flow 

## Layout 

- 'app/api/'             - HTTP routes (FastAPI routes, request/response , schemas)
- 'app/services/'        - business logic , orchestration
- 'app/domain/'          - pure models , no framworks important
- 'app/infra/'           - database , redis external clients
- 'app/core/'            - config , logging , security helpers 
- 'tests/'               - pytest


Dependencies point inward , api -> services -> domain -> infra 
Domain knows nothing about HTTP , DB , or Redis 

 
