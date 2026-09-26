import axios from "axios";
import FormData from "form-data";
import { Buffer } from "node:buffer";

const FLASK_URL = process.env.FLASK_URL || "http://127.0.0.1:5001";

export async function analyzeWithFlask(fileName: string, mimeType: string, buffer: Buffer) {
  const form = new FormData();
  form.append("file", buffer, { filename: fileName, contentType: mimeType });
  const response = await axios.post(`${FLASK_URL}/api/analyze`, form, {
    headers: form.getHeaders(), maxBodyLength: Infinity, maxContentLength: Infinity, timeout: 60_000,
  });
  return response.data;
}

export async function recoverWithFlask(fileName: string, mimeType: string, buffer: Buffer) {
  const form = new FormData();
  form.append("file", buffer, { filename: fileName, contentType: mimeType });
  return axios.post(`${FLASK_URL}/api/recovery`, form, {
    headers: form.getHeaders(), maxBodyLength: Infinity, maxContentLength: Infinity,
    timeout: 180_000, responseType: "arraybuffer", validateStatus: () => true,
  });
}

export async function reconstructWithFlask(
  files: Array<{ fileName: string; mimeType: string; buffer: Buffer }>,
  outputName: string,
) {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file.buffer, { filename: file.fileName, contentType: file.mimeType });
  }
  form.append("outputName", outputName);
  return axios.post(`${FLASK_URL}/api/fragments/reconstruct`, form, {
    headers: form.getHeaders(),
    maxBodyLength: Infinity,
    maxContentLength: Infinity,
    timeout: 180_000,
    responseType: "arraybuffer",
    validateStatus: () => true,
  });
}
