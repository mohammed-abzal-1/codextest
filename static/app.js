const singleEmail = document.getElementById('singleEmail');
const checkOne = document.getElementById('checkOne');
const singleResult = document.getElementById('singleResult');

const batchEmails = document.getElementById('batchEmails');
const checkBatch = document.getElementById('checkBatch');
const downloadCsv = document.getElementById('downloadCsv');
const summary = document.getElementById('summary');
const tableBody = document.querySelector('#resultsTable tbody');

let lastCsv = '';

checkOne.addEventListener('click', async () => {
  const resp = await fetch('/api/validate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: singleEmail.value }),
  });
  const data = await resp.json();
  singleResult.textContent = JSON.stringify(data, null, 2);
});

checkBatch.addEventListener('click', async () => {
  const resp = await fetch('/api/validate-batch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ emails: batchEmails.value }),
  });
  const data = await resp.json();

  lastCsv = data.csv || '';
  downloadCsv.disabled = !lastCsv;

  summary.innerHTML = `<p>Total: ${data.summary.total} | Valid: ${data.summary.valid} | Risky: ${data.summary.risky} | Invalid: ${data.summary.invalid}</p>`;

  tableBody.innerHTML = '';
  data.results.forEach((row) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${row.email}</td>
      <td class="${row.status}">${row.status}</td>
      <td>${row.score}</td>
      <td>${row.has_dns_record ? 'yes' : 'no'}</td>
      <td>${row.suggested_correction || '-'}</td>
      <td>${row.reason}</td>
    `;
    tableBody.appendChild(tr);
  });
});

downloadCsv.addEventListener('click', () => {
  const blob = new Blob([lastCsv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'validation-results.csv';
  link.click();
  URL.revokeObjectURL(url);
});
