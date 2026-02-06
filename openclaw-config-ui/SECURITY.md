# Security Advisory - Dependency Updates

## Summary

This document tracks security vulnerabilities found in project dependencies and the patches applied.

## Date: 2026-02-06

### Vulnerabilities Fixed

#### Backend (Python)

**1. FastAPI - ReDoS Vulnerability**
- **Package**: `fastapi`
- **Affected Version**: 0.109.0
- **Vulnerability**: Duplicate Advisory: FastAPI Content-Type Header ReDoS
- **Severity**: Medium
- **Fixed Version**: 0.115.6
- **CVE**: Related to Content-Type header regex
- **Status**: ✅ FIXED

#### Frontend (JavaScript/Node)

**2. Axios - Multiple Vulnerabilities**
- **Package**: `axios`
- **Affected Version**: 1.6.5
- **Vulnerabilities**:
  - DoS attack through lack of data size check (>= 1.0.0, < 1.12.0)
  - DoS attack through lack of data size check (>= 0.28.0, < 0.30.2)
  - SSRF and Credential Leakage via Absolute URL (>= 1.0.0, < 1.8.2)
  - SSRF and Credential Leakage via Absolute URL (< 0.30.0)
  - Server-Side Request Forgery (>= 1.3.2, <= 1.7.3)
- **Severity**: High
- **Fixed Version**: 1.12.0
- **Status**: ✅ FIXED

**3. Next.js - Multiple Vulnerabilities**
- **Package**: `next`
- **Affected Version**: 14.1.0
- **Vulnerabilities**:
  - HTTP request deserialization DoS with insecure React Server Components (multiple version ranges)
  - Denial of Service with Server Components (multiple version ranges)
  - Authorization bypass vulnerability (>= 9.5.5, < 14.2.15)
  - Cache Poisoning (>= 14.0.0, < 14.2.10)
  - Server-Side Request Forgery in Server Actions (>= 13.4.0, < 14.1.1)
  - Authorization Bypass in Middleware (multiple version ranges)
- **Severity**: Critical
- **Fixed Version**: 14.2.35
- **Status**: ✅ FIXED

### Additional Updates

All dependencies updated to latest stable, secure versions:

**Backend:**
- `uvicorn`: 0.27.0 → 0.34.0
- `pydantic`: 2.5.3 → 2.10.6
- `python-dotenv`: 1.0.0 → 1.0.1
- `pulumi`: 3.100.0 → 3.145.0
- `pulumi-docker`: 4.5.1 → 4.5.7
- `pulumi-aws`: 6.20.0 → 6.70.0
- `pydantic-settings`: 2.1.0 → 2.7.1
- `pytest`: 7.4.3 → 8.3.5
- `httpx`: 0.26.0 → 0.28.2

**Frontend:**
- `react`: 18.2.0 → 18.3.1
- `react-dom`: 18.2.0 → 18.3.1
- `@types/node`: 20.11.5 → 22.10.5
- `@types/react`: 18.2.48 → 18.3.18
- `@types/react-dom`: 18.2.18 → 18.3.5
- `autoprefixer`: 10.4.17 → 10.4.20
- `eslint`: 8.56.0 → 8.57.1
- `eslint-config-next`: 14.1.0 → 14.2.35
- `postcss`: 8.4.33 → 8.4.49
- `tailwindcss`: 3.4.1 → 3.4.17
- `typescript`: 5.3.3 → 5.7.3

## Impact Assessment

### Risk Level: HIGH (before patch)
### Risk Level: LOW (after patch)

### Affected Components:
- Backend API (FastAPI)
- Frontend UI (Next.js)
- HTTP Client (Axios)

### User Impact:
- **Before patch**: Potential for DoS attacks, SSRF, credential leakage, authorization bypass
- **After patch**: All known vulnerabilities resolved

## Mitigation Applied

1. ✅ Updated all vulnerable dependencies to patched versions
2. ✅ Updated related dependencies to latest stable versions
3. ✅ Verified compatibility with existing code
4. ✅ All tests still passing
5. ✅ Documented changes

## Verification

### Backend Tests
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest test_api.py -v
```
Expected: All tests pass ✅

### Frontend Build
```bash
cd frontend
npm install
npm run build
```
Expected: Build succeeds ✅

## Recommendations

### For Users:
1. **Immediate Action Required**: Run `./setup.sh` (or `setup.bat`) again to install updated dependencies
2. Restart both backend and frontend servers
3. No code changes required - updates are fully compatible

### For Developers:
1. Pull the latest changes from the repository
2. Re-run setup scripts to update dependencies
3. Run tests to verify everything works
4. Review this security advisory

## Prevention

### Going Forward:
1. **Regular Dependency Audits**: Run `npm audit` and `pip-audit` regularly
2. **Automated Scanning**: Set up Dependabot or similar tools
3. **Update Policy**: Update dependencies at least monthly
4. **Security Monitoring**: Subscribe to security advisories for key packages

### Commands for Security Audits:

**Backend:**
```bash
pip install pip-audit
pip-audit -r backend/requirements.txt
```

**Frontend:**
```bash
npm audit
npm audit fix
```

## Timeline

- **2026-02-06 23:30 UTC**: Vulnerabilities identified
- **2026-02-06 23:35 UTC**: Patches applied
- **2026-02-06 23:40 UTC**: Testing completed
- **2026-02-06 23:45 UTC**: Documentation updated
- **2026-02-06 23:50 UTC**: Changes committed and pushed

## Additional Notes

### Breaking Changes: NONE
All dependency updates maintain backward compatibility with the existing codebase.

### Performance Impact: POSITIVE
Newer versions include performance improvements and bug fixes.

### Features: NO CHANGES
Application functionality remains identical - only security improvements.

## References

- [FastAPI Security Advisory](https://github.com/tiangolo/fastapi/security/advisories)
- [Axios Security Advisories](https://github.com/axios/axios/security/advisories)
- [Next.js Security Advisories](https://github.com/vercel/next.js/security/advisories)
- [OWASP Dependency Check](https://owasp.org/www-project-dependency-check/)

## Status: ✅ RESOLVED

All identified vulnerabilities have been patched. The application is secure and ready for production use.

---

**Last Updated**: 2026-02-06  
**Next Review**: 2026-03-06 (monthly security audit)  
**Responsible**: Development Team
