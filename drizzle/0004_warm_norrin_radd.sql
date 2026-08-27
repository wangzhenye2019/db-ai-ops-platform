CREATE TABLE `local_accounts` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`username` varchar(64) NOT NULL,
	`passwordHash` varchar(255) NOT NULL,
	`mustChangePassword` boolean NOT NULL DEFAULT true,
	`sessionVersion` int NOT NULL DEFAULT 1,
	`passwordChangedAt` timestamp,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `local_accounts_id` PRIMARY KEY(`id`),
	CONSTRAINT `local_accounts_userId_unique` UNIQUE(`userId`),
	CONSTRAINT `local_accounts_username_unique` UNIQUE(`username`)
);
--> statement-breakpoint
ALTER TABLE `local_accounts` ADD CONSTRAINT `local_accounts_userId_users_id_fk` FOREIGN KEY (`userId`) REFERENCES `users`(`id`) ON DELETE no action ON UPDATE no action;