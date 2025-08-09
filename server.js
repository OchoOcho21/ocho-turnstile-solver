import express from 'express';
import Solver from './solver.js';

const app = express();
app.use(express.json());

app.post('/solve', async (req, res) => {
    try {
        const { url, sitekey, invisible } = req.body;
        if (!url || !sitekey) return res.status(400).json({ error: 'Missing url or sitekey' });
        const solver = new Solver();
        const token = await solver.solve(url, sitekey, invisible || false);
        res.json({ success: true, token });
    } catch (err) {
        res.status(500).json({ success: false, error: err.message, stack: err.stack });
    }
});

app.get('/', (req, res) => {
    res.send('Turnstile solver is running');
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});