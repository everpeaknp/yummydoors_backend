import fs from "node:fs";
import path from "node:path";

const repository = fs.readFileSync(
  path.resolve("/home/ramon/projects/everacy/yummydoors_backend/app/modules/orders/repository.py"),
  "utf8",
);
const service = fs.readFileSync(
  path.resolve("/home/ramon/projects/everacy/yummydoors_backend/app/modules/orders/service.py"),
  "utf8",
);

if (!repository.includes("async def get_by_id(")) {
  throw new Error("OrderRepository is missing get_by_id.");
}

if (!service.includes("self.repo.get_by_id(order_id)")) {
  throw new Error("Merchant status update no longer uses the shared order lookup.");
}

console.log("Merchant order status update path has a real order lookup.");
