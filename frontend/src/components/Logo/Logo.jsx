import az1LogoDark from '../../assets/az1-logo-dark.png'
import az1LogoLight from '../../assets/az1-logo.png'

export default function Logo({ size = 36, className = '' }) {
  return (
    <span
      className={`relative inline-block ${className}`}
      style={{ width: size, height: size }}
    >
      <img
        src={az1LogoLight}
        alt="AZ1"
        className="absolute inset-0 h-full w-full object-contain dark:hidden"
      />
      <img
        src={az1LogoDark}
        alt="AZ1"
        className="absolute inset-0 hidden h-full w-full object-contain dark:block"
      />
    </span>
  )
}
