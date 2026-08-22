CREATE TABLE `controlled_executor_nodes` (
	`id` int AUTO_INCREMENT NOT NULL,
	`nodeKey` varchar(64) NOT NULL,
	`name` varchar(128) NOT NULL,
	`environment` enum('production','staging','test','development') NOT NULL DEFAULT 'production',
	`status` enum('online','degraded','offline','unverified') NOT NULL DEFAULT 'unverified',
	`endpoint` varchar(512),
	`zone` varchar(128),
	`capabilities` json,
	`supportedEngines` json,
	`lastHeartbeatAt` timestamp,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `controlled_executor_nodes_id` PRIMARY KEY(`id`),
	CONSTRAINT `controlled_executor_nodes_nodeKey_unique` UNIQUE(`nodeKey`)
);
--> statement-breakpoint
CREATE TABLE `database_instances` (
	`id` int AUTO_INCREMENT NOT NULL,
	`name` varchar(128) NOT NULL,
	`engine` enum('mysql','postgresql','oracle','sql_server','dameng','kingbase','oceanbase','polardb','gaussdb','tidb','goldendb','gbase','tdsql','opengauss') NOT NULL,
	`host` varchar(255) NOT NULL,
	`port` int NOT NULL,
	`databaseName` varchar(128),
	`version` varchar(80),
	`environment` enum('production','staging','test','development') NOT NULL DEFAULT 'production',
	`healthStatus` enum('healthy','warning','critical','unknown') NOT NULL DEFAULT 'unknown',
	`healthScore` int NOT NULL DEFAULT 0,
	`connectionStatus` enum('connected','degraded','disconnected','unknown') NOT NULL DEFAULT 'unknown',
	`capacityGb` int,
	`usedCapacityGb` int,
	`owner` varchar(128),
	`credentialRef` varchar(160),
	`capabilities` json,
	`tags` json,
	`lastCheckedAt` timestamp,
	`createdBy` varchar(64),
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `database_instances_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `execution_logs` (
	`id` int AUTO_INCREMENT NOT NULL,
	`executionId` int NOT NULL,
	`level` enum('info','warning','error','audit') NOT NULL DEFAULT 'info',
	`phase` varchar(64) NOT NULL DEFAULT 'control_plane',
	`message` text NOT NULL,
	`metadata` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `execution_logs_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `incident_analyses` (
	`id` int AUTO_INCREMENT NOT NULL,
	`analysisKey` varchar(64) NOT NULL,
	`alertId` int,
	`instanceId` int,
	`status` enum('completed','failed') NOT NULL,
	`model` varchar(96),
	`contextDigest` text,
	`result` json,
	`createdBy` varchar(64),
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `incident_analyses_id` PRIMARY KEY(`id`),
	CONSTRAINT `incident_analyses_analysisKey_unique` UNIQUE(`analysisKey`)
);
--> statement-breakpoint
CREATE TABLE `monitoring_integrations` (
	`id` int AUTO_INCREMENT NOT NULL,
	`name` varchar(128) NOT NULL,
	`provider` enum('zabbix','prometheus','xxl_job') NOT NULL,
	`endpoint` varchar(512) NOT NULL,
	`status` enum('connected','degraded','disconnected','unconfigured') NOT NULL DEFAULT 'unconfigured',
	`secretRef` varchar(160),
	`mapping` json,
	`lastSyncAt` timestamp,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `monitoring_integrations_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `notification_events` (
	`id` int AUTO_INCREMENT NOT NULL,
	`category` varchar(64) NOT NULL,
	`severity` enum('critical','high','medium','low','info') NOT NULL,
	`title` varchar(255) NOT NULL,
	`content` text NOT NULL,
	`status` enum('delivered','failed','pending') NOT NULL DEFAULT 'pending',
	`sourceExecutionKey` varchar(64),
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`deliveredAt` timestamp,
	CONSTRAINT `notification_events_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `operational_alerts` (
	`id` int AUTO_INCREMENT NOT NULL,
	`externalId` varchar(128),
	`integrationId` int,
	`instanceId` int,
	`title` varchar(255) NOT NULL,
	`severity` enum('critical','high','medium','low','info') NOT NULL DEFAULT 'medium',
	`status` enum('open','acknowledged','resolved') NOT NULL DEFAULT 'open',
	`metric` varchar(128),
	`currentValue` varchar(128),
	`threshold` varchar(128),
	`context` json,
	`occurredAt` timestamp NOT NULL DEFAULT (now()),
	`resolvedAt` timestamp,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `operational_alerts_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `runbook_executions` (
	`id` int AUTO_INCREMENT NOT NULL,
	`executionKey` varchar(64) NOT NULL,
	`runbookId` int,
	`templateKey` varchar(64),
	`runbookTitle` varchar(160) NOT NULL,
	`instanceId` int,
	`executorNodeId` int,
	`category` enum('deployment','backup_recovery','inspection','self_healing') NOT NULL,
	`riskLevel` enum('low','medium','high','critical') NOT NULL,
	`status` enum('awaiting_approval','queued','dispatched','running','succeeded','failed','cancelled') NOT NULL DEFAULT 'awaiting_approval',
	`input` json,
	`confirmationRequired` boolean NOT NULL DEFAULT true,
	`approvalNote` text,
	`approvedBy` varchar(64),
	`approvedAt` timestamp,
	`dispatchedAt` timestamp,
	`startedAt` timestamp,
	`completedAt` timestamp,
	`result` json,
	`createdBy` varchar(64),
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `runbook_executions_id` PRIMARY KEY(`id`),
	CONSTRAINT `runbook_executions_executionKey_unique` UNIQUE(`executionKey`)
);
--> statement-breakpoint
CREATE TABLE `runbooks` (
	`id` int AUTO_INCREMENT NOT NULL,
	`title` varchar(160) NOT NULL,
	`category` enum('deployment','backup_recovery','inspection','self_healing') NOT NULL,
	`description` text,
	`compatibleEngines` json,
	`riskLevel` enum('low','medium','high','critical') NOT NULL DEFAULT 'medium',
	`approvalRequired` boolean NOT NULL DEFAULT true,
	`steps` json,
	`status` enum('draft','active','archived') NOT NULL DEFAULT 'draft',
	`createdBy` varchar(64),
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `runbooks_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
ALTER TABLE `execution_logs` ADD CONSTRAINT `execution_logs_executionId_runbook_executions_id_fk` FOREIGN KEY (`executionId`) REFERENCES `runbook_executions`(`id`) ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE `incident_analyses` ADD CONSTRAINT `incident_analyses_alertId_operational_alerts_id_fk` FOREIGN KEY (`alertId`) REFERENCES `operational_alerts`(`id`) ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE `incident_analyses` ADD CONSTRAINT `incident_analyses_instanceId_database_instances_id_fk` FOREIGN KEY (`instanceId`) REFERENCES `database_instances`(`id`) ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE `operational_alerts` ADD CONSTRAINT `operational_alerts_integrationId_monitoring_integrations_id_fk` FOREIGN KEY (`integrationId`) REFERENCES `monitoring_integrations`(`id`) ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE `operational_alerts` ADD CONSTRAINT `operational_alerts_instanceId_database_instances_id_fk` FOREIGN KEY (`instanceId`) REFERENCES `database_instances`(`id`) ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE `runbook_executions` ADD CONSTRAINT `runbook_executions_runbookId_runbooks_id_fk` FOREIGN KEY (`runbookId`) REFERENCES `runbooks`(`id`) ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE `runbook_executions` ADD CONSTRAINT `runbook_executions_instanceId_database_instances_id_fk` FOREIGN KEY (`instanceId`) REFERENCES `database_instances`(`id`) ON DELETE no action ON UPDATE no action;--> statement-breakpoint
