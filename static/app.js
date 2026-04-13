const singleEmail = document.getElementById('singleEmail');
const checkOne = document.getElementById('checkOne');
const singleResult = document.getElementById('singleResult');

const batchEmails = document.getElementById('batchEmails');
const checkBatch = document.getElementById('checkBatch');
const summary = document.getElementById('summary');
const tableBody = document.querySelector('#resultsTable tbody');

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

  summary.innerHTML = `<p>Total: ${data.summary.total} | Valid: ${data.summary.valid} | Risky: ${data.summary.risky} | Invalid: ${data.summary.invalid}</p>`;

  tableBody.innerHTML = '';
  data.results.forEach((row) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${row.email}</td>
      <td class="${row.status}">${row.status}</td>
      <td>${row.score}</td>
      <td>${row.reason}</td>
    `;
    tableBody.appendChild(tr);
  });
});
