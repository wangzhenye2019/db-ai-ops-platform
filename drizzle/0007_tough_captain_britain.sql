CREATE TABLE `change_requests` (
	`id` int AUTO_INCREMENT NOT NULL,
	`requestKey` varchar(64) NOT NULL,
	`title` varchar(160) NOT NULL,
	`instanceId` int,
	`serverAssetId` int,
	`engine` varchar(32) NOT NULL,
	`sqlText` text NOT NULL,
	`rollbackSql` text,
	`riskLevel` enum('low','medium','high','critical') NOT NULL DEFAULT 'medium',
	`status` enum('draft','pending_review','approved','rejected','executing','succeeded','failed','cancelled') NOT NULL DEFAULT 'draft',
	`reviewResult` json,
	`plan` json,
	`approver` varchar(64),
	`approvedAt` timestamp,
	`linkedExecutionKey` varchar(64),
	`requestedBy` varchar(64),
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `change_requests_id` PRIMARY KEY(`id`),
	CONSTRAINT `change_requests_requestKey_unique` UNIQUE(`requestKey`)
);
--> statement-breakpoint
CREATE TABLE `query_audit_records` (
	`id` int AUTO_INCREMENT NOT NULL,
	`queryKey` varchar(64) NOT NULL,
	`instanceId` int,
	`engine` varchar(32) NOT NULL,
	`sqlHash` varchar(128) NOT NULL,
	`status` enum('pending','approved','rejected','executed','failed') NOT NULL DEFAULT 'pending',
	`maskedColumns` json,
	`requestedBy` varchar(64),
	`reviewedBy` varchar(64),
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `query_audit_records_id` PRIMARY KEY(`id`),
	CONSTRAINT `query_audit_records_queryKey_unique` UNIQUE(`queryKey`)
);
--> statement-breakpoint
CREATE TABLE `server_assets` (
	`id` int AUTO_INCREMENT NOT NULL,
	`name` varchar(128) NOT NULL,
	`hostname` varchar(255) NOT NULL,
	`ipAddress` varchar(64),
	`operatingSystem` varchar(128),
	`environment` enum('production','staging','test','development') NOT NULL DEFAULT 'production',
	`status` enum('online','degraded','offline','unknown') NOT NULL DEFAULT 'unknown',
	`zone` varchar(128),
	`owner` varchar(128),
	`credentialRef` varchar(160),
	`capabilities` json,
	`metadata` json,
	`lastCheckedAt` timestamp,
	`createdBy` varchar(64),
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `server_assets_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `sql_review_policies` (
	`id` int AUTO_INCREMENT NOT NULL,
	`name` varchar(128) NOT NULL,
	`engine` varchar(32),
	`enabled` boolean NOT NULL DEFAULT true,
	`rules` json,
	`createdBy` varchar(64),
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `sql_review_policies_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
ALTER TABLE `change_requests` ADD CONSTRAINT `change_requests_instanceId_database_instances_id_fk` FOREIGN KEY (`instanceId`) REFERENCES `database_instances`(`id`) ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE `change_requests` ADD CONSTRAINT `change_requests_serverAssetId_server_assets_id_fk` FOREIGN KEY (`serverAssetId`) REFERENCES `server_assets`(`id`) ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE `query_audit_records` ADD CONSTRAINT `query_audit_records_instanceId_database_instances_id_fk` FOREIGN KEY (`instanceId`) REFERENCES `database_instances`(`id`) ON DELETE no action ON UPDATE no action;