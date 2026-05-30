import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from "@/components/ui/sonner";
import Dashboard from "@/components/Dashboard";

// @ROUTE_IMPORTS

function App() {
    return (
        <Router>
            <div className="min-h-screen bg-background text-foreground font-sans antialiased">
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/dashboard" element={<Dashboard />} />
                    {/* @ROUTE_REGISTER - Integrator injects new routes here */}
                </Routes>
                <Toaster />
            </div>
        </Router>
    );
}

export default App;
