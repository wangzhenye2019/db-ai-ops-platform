CREATE TABLE `monitoring_metric_snapshots` (
	`id` int AUTO_INCREMENT NOT NULL,
	`integrationId` int,
	`instanceId` int,
	`metric` varchar(128) NOT NULL,
	`value` varchar(128) NOT NULL,
	`unit` varchar(32),
	`labels` json,
	`occurredAt` timestamp NOT NULL DEFAULT (now()),
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `monitoring_metric_snapshots_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
ALTER TABLE `monitoring_metric_snapshots` ADD CONSTRAINT `metric_int_fk` FOREIGN KEY (`integrationId`) REFERENCES `monitoring_integrations`(`id`) ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE `monitoring_metric_snapshots` ADD CONSTRAINT `metric_inst_fk` FOREIGN KEY (`instanceId`) REFERENCES `database_instances`(`id`) ON DELETE no action ON UPDATE no action;