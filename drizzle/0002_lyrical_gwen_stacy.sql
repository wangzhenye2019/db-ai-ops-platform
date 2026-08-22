ALTER TABLE `runbook_executions` ADD CONSTRAINT `rb_exec_node_fk` FOREIGN KEY (`executorNodeId`) REFERENCES `controlled_executor_nodes`(`id`) ON DELETE no action ON UPDATE no action;
