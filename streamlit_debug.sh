#!/bin/bash

echo "🔍 Streamlit Network Diagnostics 🌐"

# Network Interface Details
echo -e "\n1. Network Interfaces:"
ip addr show

# Check if Streamlit is installed
echo -e "\n2. Streamlit Installation:"
if command -v streamlit &> /dev/null; then
    streamlit --version
else
    echo "Streamlit is NOT installed"
fi

# Port Availability
echo -e "\n3. Port 6010 Status:"
if ss -tuln | grep :6010; then
    echo "Port 6010 is currently in use"
else
    echo "Port 6010 is available"
fi

# Suggested Debugging Commands
echo -e "\n4. Recommended Debugging Steps:"
echo "a) Run Streamlit with verbose output:"
echo "   streamlit run liver_prediction_dashboard.py --server.address 172.18.0.4 --server.port 6010 --logger.level=debug"

echo -e "\nb) Check network accessibility:"
echo "   curl http://172.18.0.4:6010"

# Firewall Check
echo -e "\n5. Firewall Status:"
if command -v ufw &> /dev/null; then
    ufw status
elif command -v firewall-cmd &> /dev/null; then
    firewall-cmd --state
else
    echo "Firewall check not available"
fi

# Python and pip versions
echo -e "\n6. Python Environment:"
python3 --version
pip3 --version

# Detect potential issues
echo -e "\n7. Potential Issues to Check:"
echo "- Ensure all required libraries are installed"
echo "- Verify Streamlit can run without errors"
echo "- Check for any network restrictions"
