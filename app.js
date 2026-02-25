const STORAGE_KEY = 'strategies';

const seedStrategies = [
  { id: 1, name: 'Momentum Core', symbol: 'SPY', shortWindow: 20, longWindow: 100, threshold: 1.2 },
  { id: 2, name: 'Slow Trend Guard', symbol: 'QQQ', shortWindow: 30, longWindow: 150, threshold: 0.8 },
];

const navDashboard = document.getElementById('navDashboard');
const navSimulation = document.getElementById('navSimulation');
const dashboardView = document.getElementById('dashboardView');
const simulationView = document.getElementById('simulationView');
const strategyTableBody = document.getElementById('strategyTableBody');
const simulationForm = document.getElementById('simulationForm');
const message = document.getElementById('message');
const addStrategyButton = document.getElementById('addStrategyButton');
const resultsSection = document.getElementById('results');
const resultStats = document.getElementById('resultStats');

let lastSimulatedSignature = '';

function formatDate(date) {
  return date.toISOString().slice(0, 10);
}

function getDefaultDates() {
  const end = new Date();
  const start = new Date(end);
  start.setFullYear(start.getFullYear() - 2);
  return { startDate: formatDate(start), endDate: formatDate(end) };
}

function loadStrategies() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) {
    try {
      return JSON.parse(stored);
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(seedStrategies));
  return [...seedStrategies];
}

function saveStrategies(strategies) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(strategies));
}

function getStrategies() {
  return loadStrategies();
}

function setMessage(text, type = '') {
  message.textContent = text;
  message.className = `message ${type}`.trim();
}

function switchView(view) {
  const showDashboard = view === 'dashboard';
  dashboardView.classList.toggle('active', showDashboard);
  simulationView.classList.toggle('active', !showDashboard);
  navDashboard.classList.toggle('active', showDashboard);
  navSimulation.classList.toggle('active', !showDashboard);
}

function renderDashboard() {
  const strategies = getStrategies();
  strategyTableBody.innerHTML = '';

  for (const strategy of strategies) {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${strategy.name}</td>
      <td>${strategy.symbol}</td>
      <td>${strategy.shortWindow}</td>
      <td>${strategy.longWindow}</td>
      <td>${strategy.threshold}</td>
      <td>
        <div class="row-actions">
          <button class="simulate" data-action="simulate" data-id="${strategy.id}">Simulate</button>
          <button class="delete" data-action="delete" data-id="${strategy.id}">Delete</button>
        </div>
      </td>
    `;
    strategyTableBody.appendChild(row);
  }
}

function collectFormValues() {
  return Object.fromEntries(new FormData(simulationForm).entries());
}

function clearInvalidFlags() {
  for (const input of simulationForm.elements) {
    if (input.tagName === 'INPUT') {
      input.classList.remove('invalid');
    }
  }
}

function validateForm(requireSimulationMatch = false) {
  clearInvalidFlags();
  const values = collectFormValues();
  const missing = [];

  for (const [key, value] of Object.entries(values)) {
    if (!String(value).trim()) missing.push(key);
  }

  const long = Number(values.longWindow);
  const short = Number(values.shortWindow);
  if (short >= long) {
    missing.push('shortWindow', 'longWindow');
    setMessage('Short MA window must be less than Long MA window.', 'error');
  }

  if (missing.length) {
    const names = [...new Set(missing)];
    for (const name of names) {
      const input = simulationForm.elements.namedItem(name);
      if (input?.classList) input.classList.add('invalid');
    }
    if (!message.textContent) {
      setMessage('Please fill in the missing fields before continuing.', 'error');
    }
    return null;
  }

  const signature = JSON.stringify(values);
  if (requireSimulationMatch && signature !== lastSimulatedSignature) {
    setMessage('Please run Simulate with the current field values before adding this strategy.', 'error');
    return null;
  }
  return values;
}

function fillSimulationForm(strategy) {
  const defaults = getDefaultDates();
  simulationForm.elements.namedItem('name').value = strategy.name;
  simulationForm.elements.namedItem('symbol').value = strategy.symbol;
  simulationForm.elements.namedItem('shortWindow').value = strategy.shortWindow;
  simulationForm.elements.namedItem('longWindow').value = strategy.longWindow;
  simulationForm.elements.namedItem('threshold').value = strategy.threshold;
  simulationForm.elements.namedItem('tradeCost').value = 1;
  simulationForm.elements.namedItem('startingAmount').value = 10000;
  simulationForm.elements.namedItem('startDate').value = defaults.startDate;
  simulationForm.elements.namedItem('endDate').value = defaults.endDate;
}

function renderSimulation(values) {
  const startingAmount = Number(values.startingAmount);
  const volatilityBoost = Math.min(Number(values.threshold), 5) / 100;
  const trendBonus = (Number(values.longWindow) - Number(values.shortWindow)) / 1000;
  const grossReturnPct = 0.08 + trendBonus + volatilityBoost;
  const tradeCost = Number(values.tradeCost) * 20;
  const endingAmount = startingAmount * (1 + grossReturnPct) - tradeCost;

  resultStats.innerHTML = `
    <div class="stat"><strong>Strategy:</strong> ${values.name}</div>
    <div class="stat"><strong>Date Range:</strong> ${values.startDate} → ${values.endDate}</div>
    <div class="stat"><strong>Estimated Return:</strong> ${(grossReturnPct * 100).toFixed(2)}%</div>
    <div class="stat"><strong>Ending Balance:</strong> $${endingAmount.toFixed(2)}</div>
  `;
  resultsSection.classList.remove('hidden');
}

function runSimulateFlow(values) {
  renderSimulation(values);
  lastSimulatedSignature = JSON.stringify(values);
  setMessage('Simulation complete. You can now add this strategy to your dashboard.', 'success');
}

function addStrategyToDashboard(values) {
  const strategies = getStrategies();
  const newId = Math.max(0, ...strategies.map((s) => Number(s.id) || 0)) + 1;
  strategies.push({
    id: newId,
    name: values.name,
    symbol: values.symbol,
    shortWindow: Number(values.shortWindow),
    longWindow: Number(values.longWindow),
    threshold: Number(values.threshold),
  });
  saveStrategies(strategies);
  renderDashboard();
}

strategyTableBody.addEventListener('click', (event) => {
  const button = event.target.closest('button');
  if (!button) return;

  const id = Number(button.dataset.id);
  const action = button.dataset.action;
  const strategies = getStrategies();

  if (action === 'delete') {
    const next = strategies.filter((s) => s.id !== id);
    saveStrategies(next);
    renderDashboard();
    return;
  }

  if (action === 'simulate') {
    const strategy = strategies.find((s) => s.id === id);
    if (!strategy) return;
    fillSimulationForm(strategy);
    switchView('simulation');
    clearInvalidFlags();
    const values = collectFormValues();
    runSimulateFlow(values);
  }
});

simulationForm.addEventListener('submit', (event) => {
  event.preventDefault();
  setMessage('');
  const values = validateForm(false);
  if (!values) return;
  runSimulateFlow(values);
});

addStrategyButton.addEventListener('click', () => {
  setMessage('');
  const values = validateForm(true);
  if (!values) return;
  addStrategyToDashboard(values);
  setMessage('Strategy added to dashboard.', 'success');
  switchView('dashboard');
});

navDashboard.addEventListener('click', () => switchView('dashboard'));
navSimulation.addEventListener('click', () => switchView('simulation'));

renderDashboard();
switchView('dashboard');
