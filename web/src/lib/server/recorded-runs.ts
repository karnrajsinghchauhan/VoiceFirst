// Runs recorded from the engine by web/scripts/record_demo.py (npm run record:demo).
import type { DemoRun, ScenarioId } from "@/lib/demo-types";
import angryRefund from "@/content/demo-runs/angry_refund.json";
import cardNumber from "@/content/demo-runs/card_number.json";
import cars24Inspection from "@/content/demo-runs/cars24_inspection.json";
import cars24Reschedule from "@/content/demo-runs/cars24_reschedule.json";
import childAnswers from "@/content/demo-runs/child_answers.json";
import confirmation from "@/content/demo-runs/confirmation.json";
import failedUpi from "@/content/demo-runs/failed_upi.json";
import stopCalling from "@/content/demo-runs/stop_calling.json";

export const RECORDED_RUNS: Record<ScenarioId, DemoRun> = {
  failed_upi: failedUpi as DemoRun,
  confirmation: confirmation as DemoRun,
  angry_refund: angryRefund as DemoRun,
  stop_calling: stopCalling as DemoRun,
  child_answers: childAnswers as DemoRun,
  card_number: cardNumber as DemoRun,
  cars24_inspection: cars24Inspection as DemoRun,
  cars24_reschedule: cars24Reschedule as DemoRun,
};
