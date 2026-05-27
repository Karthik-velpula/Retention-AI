
/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
DROP TABLE IF EXISTS `alert_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alert_history` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` int DEFAULT NULL,
  `sent_by` varchar(120) NOT NULL,
  `recipient_name` varchar(120) NOT NULL,
  `recipient_email` varchar(120) NOT NULL,
  `risk_level` varchar(20) NOT NULL,
  `status` varchar(20) NOT NULL,
  `error_message` text NOT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `ix_alert_history_recipient_email` (`recipient_email`),
  KEY `ix_alert_history_student_id` (`student_id`),
  KEY `ix_alert_history_id` (`id`),
  CONSTRAINT `alert_history_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `financial`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `financial` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` int NOT NULL,
  `fee_due` float NOT NULL,
  `payment_delay_days` int NOT NULL,
  `scholarship_amount` float NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `student_id` (`student_id`),
  KEY `ix_financial_id` (`id`),
  CONSTRAINT `financial_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1342 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `intervention_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `intervention_history` (
  `id` int NOT NULL AUTO_INCREMENT,
  `intervention_id` int NOT NULL,
  `student_id` int NOT NULL,
  `changed_by` varchar(120) NOT NULL,
  `changed_fields` varchar(255) NOT NULL,
  `change_summary` text NOT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `ix_intervention_history_intervention_id` (`intervention_id`),
  KEY `ix_intervention_history_student_id` (`student_id`),
  KEY `ix_intervention_history_id` (`id`),
  CONSTRAINT `intervention_history_ibfk_1` FOREIGN KEY (`intervention_id`) REFERENCES `interventions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `intervention_history_ibfk_2` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `interventions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `interventions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` int NOT NULL,
  `contacted_student` tinyint(1) NOT NULL,
  `parent_informed` tinyint(1) NOT NULL,
  `counselor_assigned` tinyint(1) NOT NULL,
  `fee_issue_escalated` tinyint(1) NOT NULL,
  `next_follow_up_date` date DEFAULT NULL,
  `follow_up_outcome` varchar(20) DEFAULT NULL,
  `status` varchar(20) NOT NULL,
  `resolved_at` datetime DEFAULT NULL,
  `notes` varchar(500) NOT NULL,
  `updated_by` varchar(120) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_interventions_student_id` (`student_id`),
  KEY `ix_interventions_id` (`id`),
  CONSTRAINT `interventions_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `lms_activity`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_activity` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` int NOT NULL,
  `weekly_logins` int NOT NULL,
  `avg_time_spent` float NOT NULL,
  `assignment_submission_rate` float NOT NULL,
  `missed_assignments` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `student_id` (`student_id`),
  KEY `ix_lms_activity_id` (`id`),
  CONSTRAINT `lms_activity_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1342 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `password_reset_otps`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `password_reset_otps` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `otp_code` varchar(6) NOT NULL,
  `purpose` varchar(40) NOT NULL,
  `expires_at` datetime NOT NULL,
  `used_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `ix_password_reset_otps_id` (`id`),
  KEY `ix_password_reset_otps_otp_code` (`otp_code`),
  KEY `ix_password_reset_otps_user_id` (`user_id`),
  CONSTRAINT `password_reset_otps_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `predictions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `predictions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` int NOT NULL,
  `risk_score` float NOT NULL,
  `risk_level` varchar(20) NOT NULL,
  `model_name` varchar(50) NOT NULL,
  `explanation` varchar(1000) NOT NULL,
  `feature_importance` json NOT NULL,
  `recommendations` json NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `student_id` (`student_id`),
  KEY `ix_predictions_id` (`id`),
  CONSTRAINT `predictions_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `students`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `students` (
  `id` int NOT NULL AUTO_INCREMENT,
  `registration_number` varchar(20) NOT NULL,
  `name` varchar(120) NOT NULL,
  `email` varchar(120) NOT NULL,
  `counselor_name` varchar(120) NOT NULL,
  `codechef_username` varchar(100) NOT NULL,
  `codechef_contests_participated` int NOT NULL,
  `codechef_problems_solved` int NOT NULL,
  `codechef_participation_status` varchar(30) NOT NULL,
  `codechef_last_synced_at` datetime DEFAULT NULL,
  `section` varchar(20) NOT NULL,
  `gender` varchar(20) NOT NULL,
  `age` int DEFAULT NULL,
  `gpa` float NOT NULL,
  `attendance` float NOT NULL,
  `marks` float NOT NULL,
  `pre_t1_marks` float NOT NULL,
  `t1_marks` float NOT NULL,
  `t2_marks` float NOT NULL,
  `t3_marks` float NOT NULL,
  `t4_marks` float NOT NULL,
  `t5_marks` float NOT NULL,
  `department` varchar(100) NOT NULL,
  `year` int NOT NULL,
  `career_interest` varchar(120) NOT NULL,
  `skills` varchar(255) NOT NULL,
  `student_mobile` varchar(30) NOT NULL DEFAULT '',
  `parent_mobile` varchar(30) NOT NULL DEFAULT '',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_students_registration_number` (`registration_number`),
  KEY `ix_students_id` (`id`),
  KEY `ix_students_email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=1342 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `subject_attendance`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `subject_attendance` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` int NOT NULL,
  `subject_name` varchar(120) NOT NULL,
  `attendance_percentage` float NOT NULL,
  `pre_t1_marks` float NOT NULL,
  `t1_marks` float NOT NULL,
  `t2_marks` float NOT NULL,
  `t3_marks` float NOT NULL,
  `t4_marks` float NOT NULL,
  `t5_marks` float NOT NULL,
  `t5_assignment_1` float NOT NULL,
  `t5_assignment_2` float NOT NULL,
  `t5_assignment_3` float NOT NULL,
  `t5_assignment_4` float NOT NULL,
  `total_marks` float NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_subject_attendance_student_id` (`student_id`),
  KEY `ix_subject_attendance_id` (`id`),
  CONSTRAINT `subject_attendance_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=33378 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `username` varchar(40) DEFAULT NULL,
  `email` varchar(120) NOT NULL,
  `password` varchar(255) NOT NULL,
  `role` varchar(20) NOT NULL,
  `security_grid` varchar(1000) NOT NULL,
  `last_login_at` datetime DEFAULT NULL,
  `token_version` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_email` (`email`),
  UNIQUE KEY `ix_users_username` (`username`),
  KEY `ix_users_id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=58 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

