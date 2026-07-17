/**
 * T-3096: jest-axe accessibility assertions for the most significantly
 * fixed components (T-3076..T-3085 audit).
 *
 * NOTE: this repo has no jest runner configured (no "test" script, no jest
 * config, no @testing-library/react) — see package.json. Per the task
 * contract, only `jest-axe` was added as a devDependency; a full jest +
 * @testing-library/react + jsdom setup was intentionally NOT added since
 * that's a second, bigger decision (test runner choice/config) outside this
 * trimmed a11y task. This file is written in the standard jest + RTL shape
 * so it runs unmodified once that infra lands; today `npx jest` will fail
 * with "jest: command not found" rather than a real pass/fail.
 *
 * ponytail: no test runner installed here, wire jest + @testing-library/react
 * in when the repo adopts a test runner; don't invent a parallel one for this task.
 */
import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import LoginPage from '../app/login/page';
import SearchFilter from '../components/SearchFilter';
import OrgMemberManagement from '../components/OrgMemberManagement';

expect.extend(toHaveNoViolations);

describe('accessibility', () => {
  it('login page has no axe violations (labeled inputs, alert region)', async () => {
    const { container } = render(<LoginPage />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('SearchFilter has no axe violations (labeled query/type/date fields)', async () => {
    const { container } = render(<SearchFilter onSearch={() => {}} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('OrgMemberManagement has no axe violations (table th scope, alert region)', async () => {
    const { container } = render(<OrgMemberManagement />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
