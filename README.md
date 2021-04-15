# ApacheFlaskApp

Aplikacja webowa we Flasku postawiona na serwerze Apache. Umożliwia proste zarządzania notatkami z naciskiem na bezpieczeństwo użytkownika. 

Aby uruchomić aplikację należy :
1) stanąć w folderze z aplikacją
2) wpisać: docker-compose up --build
3) Następnie wejść do konsoli serwera (obrazu docker)
4) wpisać: cd ../../../
5) wpisać: ./redis-6.0.9/src/redis-server --port 6379 &
6) Aplikacja powinna być dostępna pod linkiem: https://localhost:8080/