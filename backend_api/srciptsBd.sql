-- 1. Crear tabla Role
CREATE TABLE Role (
    Id SERIAL PRIMARY KEY,
    RoleName VARCHAR(100) NOT NULL
);

-- 2. Crear tabla User (Se usan comillas dobles porque 'User' es una palabra reservada en Postgres)
CREATE TABLE "User" (
    Id SERIAL PRIMARY KEY,
    rel_role_user INT NOT NULL,
    Name VARCHAR(100) NOT NULL,
    LastName VARCHAR(100) NOT NULL,
    Email VARCHAR(255) UNIQUE NOT NULL,
    Password VARCHAR(255) NOT NULL,
    FOREIGN KEY (rel_role_user) REFERENCES Role(Id) ON DELETE RESTRICT
);

-- 3. Plantas empresa
CREATE TABLE Warehouse (
    Id SERIAL PRIMARY KEY,
    Name VARCHAR(150) NOT NULL, 
    Address VARCHAR(255) NOT NULL,
    -- Quilicura, San Fernando, Rengo, etc..
);

-- 4. Crear tabla Zone
CREATE TABLE Zone (
    Id SERIAL PRIMARY KEY,
    NameZone VARCHAR(100) NOT NULL,
    rel_warehouse_zone INT NOT NULL,
    FOREIGN KEY (rel_warehouse_zone) REFERENCES Warehouse(Id) ON DELETE CASCADE
);

-- 5. Crear tabla Camera
CREATE TABLE Camera (
    Id SERIAL PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Active BOOLEAN DEFAULT TRUE,
    rel_zone_camera INT,
    FOREIGN KEY (rel_zone_camera) REFERENCES Zone(Id) ON DELETE SET NULL
);

-- 6. Crear tabla Door
CREATE TABLE Door (
    Id SERIAL PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    ROI TEXT, -- Usualmente se guarda como JSON o String de coordenadas
    rel_zone_door INT,
    FOREIGN KEY (rel_zone_door) REFERENCES Zone(Id) ON DELETE SET NULL
);

-- 7. Crear tabla Event
CREATE TABLE Event (
    Id SERIAL PRIMARY KEY,
    EventType VARCHAR(50),
    OpenTime TIMESTAMP NOT NULL,
    CloseTime TIMESTAMP,
    Temperature DECIMAL(5, 2), -- 3 dígitos enteros y 2 decimales (ej: 180.50)
    rel_door_event INT NOT NULL,
    FOREIGN KEY (rel_door_event) REFERENCES Door(Id) ON DELETE CASCADE
);

-- 8. Crear tabla Logs
CREATE TABLE Logs (
    uniqueId SERIAL PRIMARY KEY,
    foreignKey INT, -- Llave foránea genérica según el diagrama
    fieldname VARCHAR(150)
);