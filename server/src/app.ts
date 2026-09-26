import express from "express";
import cors from "cors";
import analysisRoutes from "./routes/analysisRoutes";
import healthRoutes from "./routes/healthRoutes";
import recoveryRoutes from "./routes/recoveryRoutes";
import fragmentRoutes from "./routes/fragmentRoutes";

const app = express();
app.use(cors());
app.use(express.json());

app.use("/api/health", healthRoutes);
app.use("/api/recovery", recoveryRoutes);
app.use("/api/analysis", analysisRoutes);
app.use("/api/fragments", fragmentRoutes);

export default app;
