CREATE DATABASE IF NOT EXISTS volunteer_mgmt;
USE volunteer_mgmt;

CREATE TABLE City (
  city_id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  state VARCHAR(100) NOT NULL
);

CREATE TABLE NGO (
  ngo_id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(150) NOT NULL,
  mission TEXT,
  city_id INT,
  contact_email VARCHAR(150),
  FOREIGN KEY (city_id) REFERENCES City(city_id)
);

CREATE TABLE Coordinator (
  coord_id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(150) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  ngo_id INT,
  FOREIGN KEY (ngo_id) REFERENCES NGO(ngo_id)
);

CREATE TABLE Volunteer (
  vol_id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(150) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  phone VARCHAR(15),
  city_id INT,
  joined_date DATE DEFAULT (CURRENT_DATE),
  total_hours INT DEFAULT 0,
  FOREIGN KEY (city_id) REFERENCES City(city_id)
);

CREATE TABLE Skill (
  skill_id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  category VARCHAR(100)
);

CREATE TABLE VolunteerSkill (
  vol_id INT,
  skill_id INT,
  proficiency_level ENUM('beginner', 'intermediate', 'expert') DEFAULT 'beginner',
  PRIMARY KEY (vol_id, skill_id),
  FOREIGN KEY (vol_id) REFERENCES Volunteer(vol_id),
  FOREIGN KEY (skill_id) REFERENCES Skill(skill_id)
);

CREATE TABLE Drive (
  drive_id INT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  description TEXT,
  drive_date DATE NOT NULL,
  location VARCHAR(200),
  city_id INT,
  ngo_id INT NOT NULL,
  coord_id INT,
  max_volunteers INT DEFAULT 50,
  current_registrations INT DEFAULT 0,
  status ENUM('upcoming', 'ongoing', 'completed', 'cancelled') DEFAULT 'upcoming',
  FOREIGN KEY (city_id) REFERENCES City(city_id),
  FOREIGN KEY (ngo_id) REFERENCES NGO(ngo_id),
  FOREIGN KEY (coord_id) REFERENCES Coordinator(coord_id)
);

CREATE TABLE Registration (
  reg_id INT PRIMARY KEY AUTO_INCREMENT,
  vol_id INT NOT NULL,
  drive_id INT NOT NULL,
  registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  status ENUM('registered', 'attended', 'cancelled') DEFAULT 'registered',
  UNIQUE KEY unique_reg (vol_id, drive_id),
  FOREIGN KEY (vol_id) REFERENCES Volunteer(vol_id),
  FOREIGN KEY (drive_id) REFERENCES Drive(drive_id)
);

CREATE TABLE Attendance (
  att_id INT PRIMARY KEY AUTO_INCREMENT,
  reg_id INT UNIQUE NOT NULL,
  checked_in_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  hours_logged DECIMAL(4,1) DEFAULT 0,
  FOREIGN KEY (reg_id) REFERENCES Registration(reg_id)
);

CREATE TABLE Certificate (
  cert_id INT PRIMARY KEY AUTO_INCREMENT,
  vol_id INT NOT NULL,
  issued_date DATE DEFAULT (CURRENT_DATE),
  total_hours_at_issue INT,
  drive_count INT,
  FOREIGN KEY (vol_id) REFERENCES Volunteer(vol_id)
);

-- Query optimization indexes
CREATE INDEX idx_ngo_city_id ON NGO(city_id);
CREATE INDEX idx_volunteer_city_id ON Volunteer(city_id);
CREATE INDEX idx_coordinator_ngo_id ON Coordinator(ngo_id);
CREATE INDEX idx_drive_city_id ON Drive(city_id);
CREATE INDEX idx_drive_ngo_id ON Drive(ngo_id);
CREATE INDEX idx_drive_coord_id ON Drive(coord_id);
CREATE INDEX idx_registration_vol_id ON Registration(vol_id);
CREATE INDEX idx_registration_drive_id ON Registration(drive_id);
CREATE INDEX idx_attendance_reg_id ON Attendance(reg_id);
CREATE INDEX idx_certificate_vol_id ON Certificate(vol_id);

DELIMITER $$

CREATE TRIGGER after_attendance_insert
AFTER INSERT ON Attendance
FOR EACH ROW
BEGIN
  UPDATE Volunteer v
  JOIN Registration r ON r.reg_id = NEW.reg_id
  SET v.total_hours = v.total_hours + NEW.hours_logged
  WHERE v.vol_id = r.vol_id;

  UPDATE Registration SET status = 'attended' WHERE reg_id = NEW.reg_id;
END$$

CREATE TRIGGER check_certificate_eligibility
AFTER UPDATE ON Volunteer
FOR EACH ROW
BEGIN
  IF NEW.total_hours >= 10 AND OLD.total_hours < 10 THEN
    INSERT INTO Certificate (vol_id, total_hours_at_issue, drive_count)
    SELECT NEW.vol_id, NEW.total_hours, COUNT(*)
    FROM Registration
    WHERE vol_id = NEW.vol_id AND status = 'attended';
  END IF;
END$$

CREATE TRIGGER check_drive_capacity
BEFORE INSERT ON Registration
FOR EACH ROW
BEGIN
  DECLARE curr INT;
  SELECT current_registrations INTO curr FROM Drive WHERE drive_id = NEW.drive_id;
  IF curr >= (SELECT max_volunteers FROM Drive WHERE drive_id = NEW.drive_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Drive is full. Registration closed.';
  END IF;
  UPDATE Drive SET current_registrations = current_registrations + 1 WHERE drive_id = NEW.drive_id;
END$$

CREATE PROCEDURE RegisterVolunteer(IN p_vol_id INT, IN p_drive_id INT, OUT p_message VARCHAR(200))
BEGIN
  DECLARE drive_status VARCHAR(20);
  DECLARE already_registered INT;

  SELECT status INTO drive_status FROM Drive WHERE drive_id = p_drive_id;
  SELECT COUNT(*) INTO already_registered FROM Registration
    WHERE vol_id = p_vol_id AND drive_id = p_drive_id;

  IF drive_status != 'upcoming' THEN
    SET p_message = 'Drive is not open for registration.';
  ELSEIF already_registered > 0 THEN
    SET p_message = 'Volunteer already registered for this drive.';
  ELSE
    INSERT INTO Registration (vol_id, drive_id) VALUES (p_vol_id, p_drive_id);
    SET p_message = 'Registration successful.';
  END IF;
END$$

CREATE PROCEDURE GetNGOImpactReport(IN p_ngo_id INT, IN p_month INT, IN p_year INT)
BEGIN
  SELECT
    d.title AS drive_name,
    d.drive_date,
    COUNT(DISTINCT r.vol_id) AS volunteers_attended,
    SUM(a.hours_logged) AS total_hours_contributed,
    AVG(a.hours_logged) AS avg_hours_per_volunteer
  FROM Drive d
  LEFT JOIN Registration r ON d.drive_id = r.drive_id AND r.status = 'attended'
  LEFT JOIN Attendance a ON a.reg_id = r.reg_id
  WHERE d.ngo_id = p_ngo_id
    AND MONTH(d.drive_date) = p_month
    AND YEAR(d.drive_date) = p_year
  GROUP BY d.drive_id
  ORDER BY d.drive_date;
END$$

CREATE FUNCTION GetTotalHours(p_vol_id INT) RETURNS INT DETERMINISTIC
BEGIN
  DECLARE hrs INT;
  SELECT COALESCE(SUM(a.hours_logged), 0) INTO hrs
  FROM Attendance a
  JOIN Registration r ON a.reg_id = r.reg_id
  WHERE r.vol_id = p_vol_id;
  RETURN hrs;
END$$

CREATE FUNCTION GetVolunteerRank(p_vol_id INT, p_city_id INT) RETURNS INT DETERMINISTIC
BEGIN
  DECLARE rnk INT;
  SELECT rank_pos INTO rnk FROM (
    SELECT vol_id, RANK() OVER (ORDER BY total_hours DESC) AS rank_pos
    FROM Volunteer WHERE city_id = p_city_id
  ) ranked WHERE vol_id = p_vol_id;
  RETURN rnk;
END$$

DELIMITER ;

-- Assignment query section:
-- 1. Nested: volunteers who attended more drives than the city average
-- SELECT name, vol_id FROM Volunteer v
-- WHERE (
--   SELECT COUNT(*) FROM Registration r
--   WHERE r.vol_id = v.vol_id AND r.status = 'attended'
-- ) > (
--   SELECT AVG(drive_count) FROM (
--     SELECT COUNT(*) AS drive_count FROM Registration r2
--     JOIN Volunteer v2 ON r2.vol_id = v2.vol_id
--     WHERE v2.city_id = v.city_id AND r2.status = 'attended'
--     GROUP BY r2.vol_id
--   ) city_avg
-- );
--
-- 2. Correlated: drives that have 0 attendance so far
-- SELECT title, drive_date FROM Drive d
-- WHERE NOT EXISTS (
--   SELECT 1 FROM Registration r
--   WHERE r.drive_id = d.drive_id AND r.status = 'attended'
-- );
--
-- 3. NGOs with no volunteer activity in the last 30 days
-- SELECT name FROM NGO n
-- WHERE n.ngo_id NOT IN (
--   SELECT DISTINCT d.ngo_id FROM Drive d
--   JOIN Registration r ON d.drive_id = r.drive_id
--   WHERE r.registered_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
-- );
