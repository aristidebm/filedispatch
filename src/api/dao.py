# create LogEntry Table here, that will contains logs informations to be exposed on the api. Table to be modeled.
# Check if we can use this query builder https://pypi.org/project/qwery/ with https://pypi.org/project/aiosqlite/

# It can be a good project to write a query-builder like https://github.com/kayak/pypika that cooled accept pydantic model
# for table schema this can be a good start  https://github.com/rafalstapinski/p3orm

# L'idee est de
# + Construire juste un wrapper qui converti les tables pydantic en table pypika et ensuite (pypika sais bien faire ce qu'il faut)
# + Ajouter des equivalent de method asynchrones aux method existante de pypika
# + Ensuite en sortie, on veut bien avoir des models pydantic car, plus facile a manipuler en python qu'avec les autre.

##### ----- Choix techniques ------------
# En attendant je vais utiliser :
# + Pypika pour la generation de requeste sql https://github.com/kayak/pypika
# + aiosqlite pour l'execution des requetes https://github.com/omnilib/aiosqlite en mode asynchrone.
# + Il faut faire la modelisation du LogEntry.
